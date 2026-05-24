import pytest

from core.exceptions import ExternalServiceError
from generation.generator import StreamingAnswerGenerator, collect_sse_events
from generation.hallucination import guard_answer
from generation.prompt_builder import REFUSAL_MESSAGE, build_prompt
from memory.session import SessionMemory
from retrieval.types import RetrievalCandidate


def candidate() -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id="course:8:chunk:0",
        document_id="course:8",
        content="Course: BCA. Description: Bachelor in Computer Application.",
        metadata={"source_type": "course", "source_id": "course:8", "title": "BCA"},
        score=0.9,
        rank=1,
        retrieval_type="rrf_final",
    )


class FailingRedis:
    async def get(self, name):
        raise RuntimeError("redis down")

    async def set(self, name, value, ex=None):
        raise RuntimeError("redis down")

    async def delete(self, name):
        raise RuntimeError("redis down")

    async def expire(self, name, time):
        raise RuntimeError("redis down")

    async def aclose(self):
        pass


class FailingLLM:
    async def stream_generate(self, *, system_prompt, user_prompt):
        raise ExternalServiceError("Ollama down")
        yield  # pragma: no cover

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_redis_failure_degrades_to_empty_history_and_false_clear() -> None:
    memory = SessionMemory(redis_client=FailingRedis())
    assert await memory.get_messages("s1") == []
    assert await memory.clear_session("s1") is False


@pytest.mark.asyncio
async def test_llm_failure_streams_safe_error_event() -> None:
    prompt = build_prompt("What is BCA?", [candidate()])
    generator = StreamingAnswerGenerator(llm_client=FailingLLM(), heartbeat_interval_seconds=0.1)

    events = await collect_sse_events(generator.stream_sse(prompt))

    assert len(events) == 1
    assert events[0].startswith("event: error")
    assert REFUSAL_MESSAGE in events[0]


def test_guard_refuses_answer_when_no_context_sources() -> None:
    result = guard_answer("BCA is Bachelor in Computer Application [1].", {})
    assert result.allowed is False
    assert result.reason == "no_sources"
    assert result.answer == REFUSAL_MESSAGE
