from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

from core.exceptions import ExternalServiceError
from core.logging import get_logger
from generation.citation import format_source_reference
from generation.llm_client import OllamaGenerationClient
from generation.prompt_builder import PromptBundle, REFUSAL_MESSAGE
from generation.hallucination import guard_answer

logger = get_logger(__name__)


@dataclass(slots=True)
class SSEEvent:
    """Server-Sent Event payload."""

    event: str
    data: dict[str, object] | str

    def format(self) -> str:
        payload = self.data if isinstance(self.data, str) else json.dumps(self.data, ensure_ascii=False)
        return f"event: {self.event}\ndata: {payload}\n\n"


@dataclass(slots=True)
class StreamingResult:
    """Final guarded result produced by a streaming answer."""

    answer: str = REFUSAL_MESSAGE
    confidence: float = 0.0
    allowed: bool = False
    reason: str = "not_completed"


class StreamingAnswerGenerator:
    """Stream LLM tokens and final source/citation events as SSE."""

    def __init__(
        self,
        *,
        llm_client: OllamaGenerationClient | None = None,
        heartbeat_interval_seconds: float = 15.0,
    ) -> None:
        if heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be > 0")
        self.llm_client = llm_client or OllamaGenerationClient()
        self._owns_llm_client = llm_client is None
        self.heartbeat_interval_seconds = heartbeat_interval_seconds

    async def close(self) -> None:
        if self._owns_llm_client:
            await self.llm_client.close()

    async def stream_sse(self, prompt: PromptBundle) -> AsyncIterator[str]:
        """Yield token/sources/done/error/heartbeat SSE events."""

        try:
            async for event in self._stream_events(prompt):
                yield event.format()
        except asyncio.CancelledError:
            logger.info("generation_stream_cancelled")
            raise
        except Exception as exc:
            logger.warning("generation_stream_error", error=str(exc))
            yield SSEEvent("error", {"message": REFUSAL_MESSAGE}).format()

    async def stream_sse_with_result(self, prompt: PromptBundle) -> AsyncIterator[tuple[str, StreamingResult | None]]:
        """Yield formatted SSE events and expose the final answer for persistence."""

        try:
            async for event in self._stream_events(prompt):
                if event.event == "done" and isinstance(event.data, dict):
                    result = StreamingResult(
                        answer=str(event.data.get("answer", REFUSAL_MESSAGE)),
                        confidence=float(event.data.get("confidence", 0.0)),
                        allowed=True,
                        reason="done",
                    )
                    yield event.format(), result
                elif event.event == "error" and isinstance(event.data, dict):
                    result = StreamingResult(
                        answer=str(event.data.get("message", REFUSAL_MESSAGE)),
                        confidence=0.0,
                        allowed=False,
                        reason="error",
                    )
                    yield event.format(), result
                else:
                    yield event.format(), None
        except asyncio.CancelledError:
            logger.info("generation_stream_cancelled")
            raise
        except Exception as exc:
            logger.warning("generation_stream_error", error=str(exc))
            result = StreamingResult(answer=REFUSAL_MESSAGE, confidence=0.0, allowed=False, reason="error")
            yield SSEEvent("error", {"message": REFUSAL_MESSAGE}).format(), result

    async def _stream_events(self, prompt: PromptBundle) -> AsyncIterator[SSEEvent]:
        answer_parts: list[str] = []
        stream = self.llm_client.stream_generate(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
        )
        pending_chunk = asyncio.create_task(stream.__anext__())

        try:
            while True:
                done, _ = await asyncio.wait({pending_chunk}, timeout=self.heartbeat_interval_seconds)
                if not done:
                    yield SSEEvent("heartbeat", {"status": "working"})
                    continue

                try:
                    chunk = pending_chunk.result()
                except StopAsyncIteration:
                    break
                except ExternalServiceError:
                    yield SSEEvent("error", {"message": REFUSAL_MESSAGE})
                    return

                pending_chunk = asyncio.create_task(stream.__anext__())

                if chunk.token:
                    answer_parts.append(chunk.token)
                    yield SSEEvent("token", {"token": chunk.token})
                if chunk.done:
                    break
        except asyncio.CancelledError:
            pending_chunk.cancel()
            raise
        finally:
            if not pending_chunk.done():
                pending_chunk.cancel()

        guarded = guard_answer("".join(answer_parts), prompt.source_map)
        yield SSEEvent(
            "sources",
            {
                "sources": guarded.citation_validation.sources
                or [format_source_reference(number, candidate) for number, candidate in prompt.source_map.items()],
                "confidence": guarded.confidence,
                "allowed": guarded.allowed,
                "reason": guarded.reason,
            },
        )
        yield SSEEvent("done", {"answer": guarded.answer, "confidence": guarded.confidence})


async def collect_sse_events(generator: AsyncIterator[str]) -> list[str]:
    """Test helper to collect an SSE stream."""

    return [event async for event in generator]
