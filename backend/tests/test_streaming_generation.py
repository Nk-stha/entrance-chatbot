import asyncio

import httpx
import pytest

from generation.generator import SSEEvent, StreamingAnswerGenerator, collect_sse_events
from generation.llm_client import LLMStreamChunk, OllamaGenerationClient
from generation.prompt_builder import REFUSAL_MESSAGE, build_prompt
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


class FakeLLMClient:
    def __init__(self, chunks=None, error=None, delay=0):
        self.chunks = chunks or []
        self.error = error
        self.delay = delay

    async def stream_generate(self, *, system_prompt, user_prompt):
        if self.error:
            raise self.error
        for chunk in self.chunks:
            if self.delay:
                await asyncio.sleep(self.delay)
            yield chunk

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_ollama_generation_client_parses_streaming_lines() -> None:
    lines = [
        b'{"response":"BCA ","done":false}\n',
        b'{"response":"course [1].","done":false}\n',
        b'{"done":true}\n',
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=httpx.ByteStream(b"".join(lines)))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama.test") as client:
        llm = OllamaGenerationClient(http_client=client)
        chunks = [chunk async for chunk in llm.stream_generate(system_prompt="sys", user_prompt="user")]

    assert [chunk.token for chunk in chunks] == ["BCA ", "course [1].", ""]
    assert chunks[-1].done is True


def test_sse_event_format() -> None:
    assert SSEEvent("token", {"token": "hello"}).format() == 'event: token\ndata: {"token": "hello"}\n\n'


@pytest.mark.asyncio
async def test_stream_sse_emits_token_sources_and_done() -> None:
    prompt = build_prompt("What is BCA?", [candidate()])
    generator = StreamingAnswerGenerator(
        llm_client=FakeLLMClient(
            [LLMStreamChunk("BCA is "), LLMStreamChunk("Bachelor in Computer Application [1]."), LLMStreamChunk("", done=True)]
        ),
        heartbeat_interval_seconds=0.5,
    )

    events = await collect_sse_events(generator.stream_sse(prompt))

    assert events[0].startswith("event: token")
    assert any("event: sources" in event and '"allowed": true' in event for event in events)
    assert events[-1].startswith("event: done")
    assert "Bachelor in Computer Application" in events[-1]


@pytest.mark.asyncio
async def test_stream_sse_refuses_uncited_answer() -> None:
    prompt = build_prompt("What is BCA?", [candidate()])
    generator = StreamingAnswerGenerator(
        llm_client=FakeLLMClient([LLMStreamChunk("BCA is Bachelor in Computer Application."), LLMStreamChunk("", done=True)]),
        heartbeat_interval_seconds=0.5,
    )

    events = await collect_sse_events(generator.stream_sse(prompt))

    assert events[-1].startswith("event: done")
    assert REFUSAL_MESSAGE in events[-1]
    assert any('"reason": "missing_citations"' in event for event in events)


@pytest.mark.asyncio
async def test_stream_sse_emits_error_on_llm_failure() -> None:
    prompt = build_prompt("What is BCA?", [candidate()])
    generator = StreamingAnswerGenerator(
        llm_client=FakeLLMClient(error=RuntimeError("ollama down")),
        heartbeat_interval_seconds=0.5,
    )

    events = await collect_sse_events(generator.stream_sse(prompt))

    assert len(events) == 1
    assert events[0].startswith("event: error")
    assert REFUSAL_MESSAGE in events[0]


@pytest.mark.asyncio
async def test_stream_sse_heartbeat_does_not_cancel_slow_generation() -> None:
    prompt = build_prompt("What is BCA?", [candidate()])
    generator = StreamingAnswerGenerator(
        llm_client=FakeLLMClient(
            [LLMStreamChunk("BCA is "), LLMStreamChunk("Bachelor in Computer Application [1]."), LLMStreamChunk("", done=True)],
            delay=0.05,
        ),
        heartbeat_interval_seconds=0.01,
    )

    events = await collect_sse_events(generator.stream_sse(prompt))

    assert any(event.startswith("event: heartbeat") for event in events)
    assert any(event.startswith("event: token") for event in events)
    assert events[-1].startswith("event: done")
    assert "Bachelor in Computer Application" in events[-1]


@pytest.mark.asyncio
async def test_stream_sse_propagates_cancellation() -> None:
    prompt = build_prompt("What is BCA?", [candidate()])
    generator = StreamingAnswerGenerator(
        llm_client=FakeLLMClient([LLMStreamChunk("token")], delay=1),
        heartbeat_interval_seconds=5,
    )
    stream = generator.stream_sse(prompt)
    task = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
