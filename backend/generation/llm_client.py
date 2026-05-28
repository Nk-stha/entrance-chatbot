from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from config import Settings, get_settings
from core.exceptions import ExternalServiceError
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class LLMStreamChunk:
    """One streamed Ollama generation chunk."""

    token: str
    done: bool = False


class OllamaGenerationClient:
    """Async Ollama client for streaming answer generation."""

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
            timeout=httpx.Timeout(120.0, connect=10.0),
        )

    async def close(self) -> None:
        if not self._external_client:
            await self.client.aclose()

    async def stream_generate(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[LLMStreamChunk]:
        """Yield tokens from Ollama `/api/generate` using stream=True."""

        prompt = f"{system_prompt}\n\n{user_prompt}"
        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": 0.2, "num_predict": 150},
        }
        logger.info("ollama_generation_stream_started", model=self.settings.ollama_model, prompt_length=len(prompt))

        try:
            async with self.client.stream("POST", "/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    token = str(data.get("response", ""))
                    done = bool(data.get("done", False))
                    if token:
                        yield LLMStreamChunk(token=token, done=False)
                    if done:
                        logger.info("ollama_generation_stream_finished")
                        yield LLMStreamChunk(token="", done=True)
                        return
        except Exception as exc:
            logger.warning("ollama_generation_stream_failed", error=str(exc))
            raise ExternalServiceError("Ollama generation stream failed") from exc
