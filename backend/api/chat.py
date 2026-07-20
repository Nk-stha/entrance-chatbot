from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.exceptions import ExternalServiceError
from core.logging import get_logger
from generation.generator import StreamingAnswerGenerator
from generation.hallucination import guard_answer
from generation.intent import classify_intent
from generation.llm_client import OllamaGenerationClient
from generation.prompt_builder import PromptBundle, build_conversational_prompt, build_prompt
from memory.session import SessionMemory
from retrieval.retriever import Retriever
from retrieval.types import RetrievalFilters

logger = get_logger(__name__)

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
    intent: str


async def build_turn_prompt(request: ChatRequest, *, recent_history: str) -> PromptBundle:
    """Classify the turn and build the matching prompt.

    Conversational turns short-circuit before the retriever is even
    constructed, so a greeting costs no embedding call, no ChromaDB scan, and
    no reranking. Knowledge turns keep the full grounded retrieval path.
    """

    intent_result = classify_intent(request.message)

    if intent_result.is_conversational:
        logger.info(
            "chat_retrieval_bypassed",
            intent=intent_result.intent.value,
            matched_rule=intent_result.matched_rule,
            session_id=request.session_id,
        )
        return build_conversational_prompt(
            request.message,
            intent=intent_result.intent,
            recent_history=recent_history,
        )

    retriever = Retriever()
    try:
        retrieved = await retriever.retrieve(
            request.message,
            filters=request.filters,
            top_k=request.top_k,
        )
    finally:
        await retriever.close()

    return build_prompt(request.message, retrieved.candidates, recent_history=recent_history)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    memory = SessionMemory()
    llm = OllamaGenerationClient()
    try:
        history = await memory.format_recent_history(request.session_id)
        prompt = await build_turn_prompt(request, recent_history=history)
        answer_parts: list[str] = []
        try:
            async for chunk in llm.stream_generate(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
            ):
                if chunk.token:
                    answer_parts.append(chunk.token)
                if chunk.done:
                    break
        except ExternalServiceError:
            # A knowledge query still surfaces 503 so the caller can retry an
            # infrastructure outage. A greeting has no dependency on retrieval
            # or sources, so it degrades to a friendly reply instead of failing.
            if not prompt.intent.is_conversational:
                raise
            logger.warning("conversational_generation_unavailable", intent=prompt.intent.value)
            answer_parts = []
        guarded = guard_answer("".join(answer_parts), prompt.source_map, intent=prompt.intent)
        await memory.add_turn(request.session_id, request.message, guarded.answer)
        return ChatResponse(
            answer=guarded.answer,
            confidence=guarded.confidence,
            sources=[] if prompt.intent.is_conversational else guarded.citation_validation.sources,
            session_id=request.session_id,
            allowed=guarded.allowed,
            reason=guarded.reason,
            intent=prompt.intent.value,
        )
    finally:
        await memory.close()
        await llm.close()


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def event_stream():
        memory = SessionMemory()
        streamer = StreamingAnswerGenerator()
        try:
            history = await memory.format_recent_history(request.session_id)
            prompt = await build_turn_prompt(request, recent_history=history)
            final_answer = None
            async for event, result in streamer.stream_sse_with_result(prompt):
                if result is not None:
                    final_answer = result.answer
                yield event
            if final_answer:
                await memory.add_turn(request.session_id, request.message, final_answer)
        finally:
            await memory.close()
            await streamer.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
