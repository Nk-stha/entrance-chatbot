from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from generation.generator import StreamingAnswerGenerator
from generation.hallucination import guard_answer
from generation.llm_client import OllamaGenerationClient
from generation.prompt_builder import build_prompt
from memory.session import SessionMemory
from retrieval.retriever import Retriever
from retrieval.types import RetrievalFilters

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=128)
    filters: RetrievalFilters | None = None
    top_k: int | None = Field(default=None, ge=1, le=10)


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    sources: list[dict[str, str]]
    session_id: str
    allowed: bool
    reason: str


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    retriever = Retriever()
    memory = SessionMemory()
    llm = OllamaGenerationClient()
    try:
        history = await memory.format_recent_history(request.session_id)
        retrieved = await retriever.retrieve(request.message, filters=request.filters, top_k=request.top_k)
        prompt = build_prompt(request.message, retrieved.candidates, recent_history=history)
        answer_parts: list[str] = []
        async for chunk in llm.stream_generate(system_prompt=prompt.system_prompt, user_prompt=prompt.user_prompt):
            if chunk.token:
                answer_parts.append(chunk.token)
            if chunk.done:
                break
        guarded = guard_answer("".join(answer_parts), prompt.source_map)
        await memory.add_turn(request.session_id, request.message, guarded.answer)
        return ChatResponse(
            answer=guarded.answer,
            confidence=guarded.confidence,
            sources=guarded.citation_validation.sources,
            session_id=request.session_id,
            allowed=guarded.allowed,
            reason=guarded.reason,
        )
    finally:
        await retriever.close()
        await memory.close()
        await llm.close()


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def event_stream():
        retriever = Retriever()
        memory = SessionMemory()
        streamer = StreamingAnswerGenerator()
        try:
            history = await memory.format_recent_history(request.session_id)
            retrieved = await retriever.retrieve(request.message, filters=request.filters, top_k=request.top_k)
            prompt = build_prompt(request.message, retrieved.candidates, recent_history=history)
            final_answer = None
            async for event, result in streamer.stream_sse_with_result(prompt):
                if result is not None:
                    final_answer = result.answer
                yield event
            if final_answer:
                await memory.add_turn(request.session_id, request.message, final_answer)
        finally:
            await retriever.close()
            await memory.close()
            await streamer.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
