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
            
        if not self.settings.enable_query_rewriter:
            return original

        prompt = f"""Rewrite the user's question into a highly effective search query for a vector database.
Focus on extracting key entities, course names (e.g., BCA, CSIT), exams (e.g., IOE, CMAT), colleges, and subjects.
Remove conversational filler. Return ONLY the search query.

Example 1:
User: Hi, can you tell me what the syllabus is for the IOE entrance exam?
Query: IOE entrance exam syllabus topics

Example 2:
User: Which computer-related courses and trainings are available?
Query: computer-related courses trainings BCA Bsc CSIT

User: {original}
Query:"""

        try:
            logger.info("query_rewrite_started", query_length=len(original))
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0, "num_predict": 30},
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
