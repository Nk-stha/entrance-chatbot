from __future__ import annotations

from collections.abc import Iterable

import httpx

from config import Settings, get_settings
from core.exceptions import ExternalServiceError
from core.logging import get_logger
from core.retry import retry_async
from models.domain import DocumentChunk

logger = get_logger(__name__)


class OllamaEmbedder:
    """Generate embeddings through Ollama outside ChromaDB."""

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
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

    async def close(self) -> None:
        if not self._external_client:
            await self.client.aclose()

    async def embed_text(self, text: str) -> list[float]:
        """Embed one text string using Ollama `/api/embeddings`."""

        if not text.strip():
            raise ValueError("text must not be empty")

        async def request_once() -> list[float]:
            logger.info("ollama_embedding_started", model=self.settings.ollama_embed_model, text_length=len(text))
            response = await self.client.post(
                "/api/embeddings",
                json={"model": self.settings.ollama_embed_model, "prompt": text},
            )
            response.raise_for_status()
            body = response.json()
            embedding = body.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise ValueError("Ollama embedding response missing embedding vector")
            vector = [float(value) for value in embedding]
            logger.info("ollama_embedding_succeeded", model=self.settings.ollama_embed_model, dimensions=len(vector))
            return vector

        try:
            return await retry_async(
                request_once,
                attempts=3,
                initial_delay_seconds=0.5,
                retryable_exceptions=(httpx.HTTPError, ValueError),
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("ollama_embedding_failed", model=self.settings.ollama_embed_model, error=str(exc))
            raise ExternalServiceError("Ollama embedding request failed") from exc

    async def embed_texts(self, texts: Iterable[str], *, batch_size: int = 8) -> list[list[float]]:
        """Embed texts in small batches to stay safe on a VPS."""

        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")

        text_list = list(texts)
        embeddings: list[list[float]] = []
        for start in range(0, len(text_list), batch_size):
            batch = text_list[start : start + batch_size]
            logger.info("ollama_embedding_batch_started", batch_size=len(batch), offset=start)
            for text in batch:
                embeddings.append(await self.embed_text(text))
            logger.info("ollama_embedding_batch_succeeded", batch_size=len(batch), offset=start)
        return embeddings

    async def embed_chunks(self, chunks: Iterable[DocumentChunk], *, batch_size: int = 8) -> list[list[float]]:
        """Embed chunk content in deterministic chunk order."""

        chunk_list = list(chunks)
        return await self.embed_texts((chunk.content for chunk in chunk_list), batch_size=batch_size)
