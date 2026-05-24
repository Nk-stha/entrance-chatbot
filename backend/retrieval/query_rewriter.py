from __future__ import annotations

import httpx

from config import Settings, get_settings
from core.logging import get_logger

logger = get_logger(__name__)


class QueryRewriter:
    """QR-RAG style query rewriting with safe fallback."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._external_client = http_client is not None
        self.client = http_client or httpx.AsyncClient(
            base_url=self.settings.ollama_base_url.rstrip("/"),
            timeout=httpx.Timeout(45.0, connect=10.0),
        )

    async def close(self) -> None:
        if not self._external_client:
            await self.client.aclose()

    async def rewrite(self, query: str) -> str:
        """Rewrite a user query for retrieval, falling back to original on failure."""

        original = query.strip()
        if not original:
            raise ValueError("query must not be empty")

        prompt = (
            "Rewrite this student admission/search question into a concise retrieval query. "
            "Keep important entities, course names, colleges, exams, subjects, and constraints. "
            "Return only the rewritten query, no explanation.\n\n"
            f"Question: {original}"
        )

        try:
            logger.info("query_rewrite_started", query_length=len(original))
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
            )
            response.raise_for_status()
            body = response.json()
            rewritten = str(body.get("response", "")).strip()
            if not rewritten:
                raise ValueError("empty rewrite response")
            logger.info("query_rewrite_succeeded", query_length=len(original), rewritten_length=len(rewritten))
            return rewritten
        except Exception as exc:
            logger.warning("query_rewrite_failed_fallback", error=str(exc))
            return original
