from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import httpx

from config import Settings, get_settings
from core.exceptions import ConfigurationError, ExternalServiceError
from core.logging import get_logger
from core.retry import retry_async
from models.domain import SourceFetchResult, SourceType

logger = get_logger(__name__)


class ResponseShape(StrEnum):
    API_PAGE = "api_page"
    SPRING_PAGE = "spring_page"
    API_LIST = "api_list"
    DIRECT_LIST = "direct_list"
    API_OBJECT = "api_object"


@dataclass(frozen=True)
class SourceEndpoint:
    source_type: SourceType
    path: str
    response_shape: ResponseShape
    id_field: str
    default_sort_by: str | None = None
    default_sort_dir: str = "asc"
    requires_auth: bool = False
    page_param: str = "page"
    size_param: str = "size"
    detail_path: str | None = None


SOURCE_ENDPOINTS: dict[SourceType, SourceEndpoint] = {
    SourceType.SYLLABUS: SourceEndpoint(
        source_type=SourceType.SYLLABUS,
        path="/syllabus",
        response_shape=ResponseShape.API_PAGE,
        id_field="syllabusId",
        default_sort_by="syllabusTitle",
        requires_auth=True,
        detail_path="/syllabus/{source_id}",
    ),
    SourceType.NOTE: SourceEndpoint(
        source_type=SourceType.NOTE,
        path="/notes",
        response_shape=ResponseShape.API_PAGE,
        id_field="noteId",
        default_sort_by="noteName",
        requires_auth=True,
        detail_path="/notes/{source_id}",
    ),
    SourceType.OLD_QUESTION: SourceEndpoint(
        source_type=SourceType.OLD_QUESTION,
        # The collection list endpoint is /old-question-collections. Appending
        # /questions makes Spring parse "questions" as the {oldQuestionId} path
        # variable and reject the request with 400 Invalid Parameter.
        path="/old-question-collections",
        response_shape=ResponseShape.API_PAGE,
        id_field="id",
        default_sort_by=None,
        default_sort_dir="desc",
        requires_auth=True,
        detail_path="/old-question-collections/{source_id}",
    ),
    SourceType.COLLEGE: SourceEndpoint(
        source_type=SourceType.COLLEGE,
        path="/colleges",
        response_shape=ResponseShape.API_PAGE,
        id_field="collegeId",
        default_sort_by="collegeName",
        detail_path="/colleges/{source_id}",
    ),
    SourceType.COURSE: SourceEndpoint(
        source_type=SourceType.COURSE,
        path="/courses",
        response_shape=ResponseShape.API_PAGE,
        id_field="courseId",
        default_sort_by="courseName",
        detail_path="/courses/{source_id}",
    ),
    SourceType.TRAINING: SourceEndpoint(
        source_type=SourceType.TRAINING,
        path="/trainings",
        response_shape=ResponseShape.API_PAGE,
        id_field="trainingName",
        default_sort_by="trainingStatus",
        detail_path="/trainings/{source_id}",
    ),
    SourceType.QUESTION_SET: SourceEndpoint(
        source_type=SourceType.QUESTION_SET,
        path="/question-sets",
        response_shape=ResponseShape.API_PAGE,
        id_field="questionSetId",
        default_sort_by="setName",
        requires_auth=True,
        detail_path="/question-sets/{source_id}",
    ),
    SourceType.QUESTION: SourceEndpoint(
        source_type=SourceType.QUESTION,
        path="/questions",
        response_shape=ResponseShape.API_PAGE,
        id_field="questionId",
        default_sort_by="category.categoryName",
        requires_auth=True,
        detail_path="/questions/{source_id}",
    ),
}


def extract_items(response_json: dict[str, Any] | list[Any], shape: ResponseShape) -> list[dict[str, Any]]:
    """Extract records from all documented Java backend response wrapper shapes."""

    if shape == ResponseShape.DIRECT_LIST:
        if not isinstance(response_json, list):
            raise ValueError("Expected direct list response")
        return [item for item in response_json if isinstance(item, dict)]

    if not isinstance(response_json, dict):
        raise ValueError(f"Expected object response for shape {shape}")

    if shape == ResponseShape.API_PAGE:
        data = response_json.get("data")
        if not isinstance(data, dict):
            raise ValueError("Expected ApiResponse.data object")
        content = data.get("content", [])
    elif shape == ResponseShape.SPRING_PAGE:
        content = response_json.get("content", [])
    elif shape == ResponseShape.API_LIST:
        content = response_json.get("data", [])
    elif shape == ResponseShape.API_OBJECT:
        data = response_json.get("data")
        content = [] if data is None else [data]
    else:
        raise ValueError(f"Unsupported response shape: {shape}")

    if not isinstance(content, list):
        raise ValueError(f"Expected list content for shape {shape}")
    return [item for item in content if isinstance(item, dict)]


def is_last_page(response_json: dict[str, Any] | list[Any], shape: ResponseShape) -> bool:
    """Return whether a paginated response is on its final page."""

    if shape not in {ResponseShape.API_PAGE, ResponseShape.SPRING_PAGE}:
        return True
    if not isinstance(response_json, dict):
        return True

    page_obj = response_json.get("data") if shape == ResponseShape.API_PAGE else response_json
    if not isinstance(page_obj, dict):
        return True

    if page_obj.get("last") is True:
        return True

    number = page_obj.get("number")
    total_pages = page_obj.get("totalPages")
    if isinstance(number, int) and isinstance(total_pages, int):
        return number >= total_pages - 1

    return True


class BackendAPIClient:
    """Async Java backend API client used by ingestion phases."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._external_client = http_client is not None
        self.client = http_client or httpx.AsyncClient(
            base_url=self.settings.backend_api_base_url.rstrip("/"),
            timeout=httpx.Timeout(20.0, connect=5.0),
        )

    async def close(self) -> None:
        if not self._external_client:
            await self.client.aclose()

    def _headers(self, endpoint: SourceEndpoint) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if endpoint.requires_auth:
            if not self.settings.chatbot_backend_jwt:
                raise ConfigurationError("CHATBOT_BACKEND_JWT is required for protected ingestion endpoints")
            headers["Authorization"] = f"Bearer {self.settings.chatbot_backend_jwt}"
        return headers

    async def _get_json(
        self,
        endpoint: SourceEndpoint,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        async def request_once() -> dict[str, Any] | list[Any]:
            logger.info(
                "backend_api_request_started",
                source_type=endpoint.source_type,
                path=endpoint.path,
                params=params or {},
                requires_auth=endpoint.requires_auth,
            )
            response = await self.client.get(
                endpoint.path,
                params=params,
                headers=self._headers(endpoint),
            )
            response.raise_for_status()
            logger.info(
                "backend_api_request_succeeded",
                source_type=endpoint.source_type,
                path=endpoint.path,
                status_code=response.status_code,
            )
            return response.json()

        try:
            return await retry_async(request_once, attempts=3, initial_delay_seconds=0.4)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "backend_api_request_failed",
                source_type=endpoint.source_type,
                path=endpoint.path,
                status_code=exc.response.status_code,
            )
            raise ExternalServiceError(
                f"Backend API returned {exc.response.status_code} for {endpoint.path}"
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "backend_api_request_failed",
                source_type=endpoint.source_type,
                path=endpoint.path,
                error=str(exc),
            )
            raise ExternalServiceError(f"Backend API request failed for {endpoint.path}") from exc

    def _page_params(self, endpoint: SourceEndpoint, page: int) -> dict[str, Any]:
        params: dict[str, Any] = {
            endpoint.page_param: page,
            endpoint.size_param: self.settings.backend_api_page_size,
        }
        if endpoint.default_sort_by:
            params["sortBy"] = endpoint.default_sort_by
            params["sortDir"] = endpoint.default_sort_dir
        elif endpoint.source_type == SourceType.OLD_QUESTION:
            params["sort"] = f"year,{endpoint.default_sort_dir}"
        return params

    def _to_fetch_result(
        self,
        endpoint: SourceEndpoint,
        item: dict[str, Any],
    ) -> SourceFetchResult:
        raw_id = item.get(endpoint.id_field)
        if raw_id is None:
            raise ValueError(f"Missing id field {endpoint.id_field} for {endpoint.source_type}")
        return SourceFetchResult(
            source_type=endpoint.source_type,
            source_id=f"{endpoint.source_type}:{raw_id}",
            payload=item,
        )

    async def fetch_source_page(
        self,
        source_type: SourceType,
        *,
        page: int = 0,
    ) -> tuple[list[SourceFetchResult], bool]:
        if page < 0:
            raise ValueError("page must be >= 0")

        endpoint = SOURCE_ENDPOINTS[source_type]
        body = await self._get_json(endpoint, params=self._page_params(endpoint, page))
        items = extract_items(body, endpoint.response_shape)
        results = [self._to_fetch_result(endpoint, item) for item in items]
        return results, is_last_page(body, endpoint.response_shape)

    async def fetch_source_by_id(
        self,
        source_type: SourceType,
        source_id: str,
    ) -> SourceFetchResult:
        """Fetch one source item for webhook-triggered incremental sync.

        Only source types with documented or known detail endpoints should configure
        `detail_path`. Other source types can still be refreshed through paginated
        source fetches until exact Java detail endpoints are confirmed.
        """

        if not source_id:
            raise ValueError("source_id must not be empty")

        endpoint = SOURCE_ENDPOINTS[source_type]
        if not endpoint.detail_path:
            raise NotImplementedError(f"No detail endpoint configured for {source_type}")

        raw_source_id = source_id.split(":", 1)[1] if ":" in source_id else source_id
        detail_endpoint = SourceEndpoint(
            source_type=endpoint.source_type,
            path=endpoint.detail_path.format(source_id=raw_source_id),
            response_shape=ResponseShape.API_OBJECT,
            id_field=endpoint.id_field,
            requires_auth=endpoint.requires_auth,
        )
        body = await self._get_json(detail_endpoint)
        items = extract_items(body, detail_endpoint.response_shape)
        if not items:
            raise ExternalServiceError(f"Backend API returned no item for {source_type}:{source_id}")
        return self._to_fetch_result(endpoint, items[0])

    async def fetch_all_source(self, source_type: SourceType) -> list[SourceFetchResult]:
        endpoint = SOURCE_ENDPOINTS[source_type]
        page = 0
        all_results: list[SourceFetchResult] = []

        while True:
            page_results, last = await self.fetch_source_page(source_type, page=page)
            all_results.extend(page_results)
            logger.info(
                "backend_api_page_fetched",
                source_type=source_type,
                page=page,
                count=len(page_results),
                last=last,
            )
            if last:
                break
            page += 1

        logger.info("backend_api_source_fetched", source_type=source_type, total=len(all_results))
        return all_results

    async def fetch_all_configured_sources(
        self,
        source_types: list[SourceType] | None = None,
    ) -> dict[SourceType, list[SourceFetchResult]]:
        selected = source_types or list(SOURCE_ENDPOINTS)
        return {source_type: await self.fetch_all_source(source_type) for source_type in selected}
