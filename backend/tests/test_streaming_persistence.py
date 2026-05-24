import pytest

from generation.generator import StreamingAnswerGenerator
from generation.llm_client import LLMStreamChunk
from generation.prompt_builder import build_prompt
from retrieval.types import RetrievalCandidate


class CitedLLM:
    async def stream_generate(self, *, system_prompt, user_prompt):
        yield LLMStreamChunk(token="BCA is ")
        yield LLMStreamChunk(token="Bachelor in Computer Application [1].")
        yield LLMStreamChunk(token="", done=True)

    async def close(self):
        pass


def candidate() -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id="course:8:chunk:0",
        document_id="course:8",
        content="BCA is Bachelor in Computer Application.",
        metadata={"source_type": "course", "source_id": "course:8", "title": "BCA"},
        score=0.9,
        rank=1,
        retrieval_type="rrf_final",
    )


@pytest.mark.asyncio
async def test_stream_sse_with_result_exposes_final_answer_for_memory_persistence() -> None:
    prompt = build_prompt("What is BCA?", [candidate()])
    generator = StreamingAnswerGenerator(llm_client=CitedLLM())

    final_answer = None
    events = []
    async for event, result in generator.stream_sse_with_result(prompt):
        events.append(event)
        if result is not None:
            final_answer = result.answer

    assert any(event.startswith("event: token") for event in events)
    assert any(event.startswith("event: done") for event in events)
    assert final_answer == "BCA is Bachelor in Computer Application [1]."
