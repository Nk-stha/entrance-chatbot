import httpx
import pytest

from config import Settings
from ingestion.api_client import BackendAPIClient, ResponseShape, extract_items, is_last_page
from models.domain import SourceType


def make_settings(jwt: str = "test.jwt.token") -> Settings:
    return Settings(
        CHATBOT_BACKEND_JWT=jwt,
        BACKEND_API_BASE_URL="http://backend.test/api/v1",
        API_KEY="test-admin-api-key",
    )


def test_extract_items_api_page() -> None:
    body = {"data": {"content": [{"id": 1}], "last": True}}
    assert extract_items(body, ResponseShape.API_PAGE) == [{"id": 1}]


def test_extract_items_spring_page() -> None:
    body = {"content": [{"id": 1}], "last": True}
    assert extract_items(body, ResponseShape.SPRING_PAGE) == [{"id": 1}]


def test_extract_items_direct_list() -> None:
    assert extract_items([{"id": 1}], ResponseShape.DIRECT_LIST) == [{"id": 1}]


def test_extract_items_api_object() -> None:
    assert extract_items({"data": {"id": 1}}, ResponseShape.API_OBJECT) == [{"id": 1}]


def test_is_last_page_uses_total_pages() -> None:
    body = {"data": {"content": [], "number": 1, "totalPages": 2}}
    assert is_last_page(body, ResponseShape.API_PAGE) is True


@pytest.mark.asyncio
async def test_fetch_source_page_adds_bearer_token_for_protected_endpoint() -> None:
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        assert request.url.params["page"] == "0"
        assert request.url.params["size"] == "100"
        return httpx.Response(
            200,
            json={
                "data": {
                    "content": [{"noteId": "n1", "noteName": "Intro"}],
                    "last": True,
                }
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://backend.test/api/v1",
    ) as http_client:
        client = BackendAPIClient(settings=make_settings(), http_client=http_client)
        results, last = await client.fetch_source_page(SourceType.NOTE)

    assert last is True
    assert results[0].source_id == "note:n1"
    assert seen_headers["authorization"] == "Bearer test.jwt.token"


@pytest.mark.asyncio
async def test_fetch_all_source_paginates_until_last() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        calls.append(page)
        return httpx.Response(
            200,
            json={
                "data": {
                    "content": [{"courseId": f"c{page}", "courseName": "Course"}],
                    "number": page,
                    "totalPages": 2,
                    "last": page == 1,
                }
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://backend.test/api/v1",
    ) as http_client:
        client = BackendAPIClient(settings=make_settings(), http_client=http_client)
        results = await client.fetch_all_source(SourceType.COURSE)

    assert calls == [0, 1]
    assert [item.source_id for item in results] == ["course:c0", "course:c1"]


@pytest.mark.asyncio
async def test_fetch_source_by_id_uses_detail_endpoint() -> None:
    seen_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return httpx.Response(
            200,
            json={"data": {"courseId": "c1", "courseName": "Course"}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://backend.test/api/v1",
    ) as http_client:
        client = BackendAPIClient(settings=make_settings(), http_client=http_client)
        result = await client.fetch_source_by_id(SourceType.COURSE, "c1")

    assert seen_paths == ["/api/v1/courses/c1"]
    assert result.source_id == "course:c1"


@pytest.mark.asyncio
async def test_fetch_source_by_id_accepts_prefixed_source_id() -> None:
    seen_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return httpx.Response(
            200,
            json={"data": {"noteId": "n1", "noteName": "Note"}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://backend.test/api/v1",
    ) as http_client:
        client = BackendAPIClient(settings=make_settings(), http_client=http_client)
        result = await client.fetch_source_by_id(SourceType.NOTE, "note:n1")

    assert seen_paths == ["/api/v1/notes/n1"]
    assert result.source_id == "note:n1"


@pytest.mark.asyncio
async def test_missing_jwt_for_protected_endpoint_fails() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
        base_url="http://backend.test/api/v1",
    ) as http_client:
        client = BackendAPIClient(settings=make_settings(jwt=""), http_client=http_client)
        with pytest.raises(Exception, match="CHATBOT_BACKEND_JWT"):
            await client.fetch_source_page(SourceType.NOTE)
