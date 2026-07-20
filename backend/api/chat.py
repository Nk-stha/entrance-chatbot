from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.exceptions import ExternalServiceError
from core.logging import get_logger
from config import get_settings
from core.timing import mark, request_timer, stage
from generation.generator import StreamingAnswerGenerator, templated_conversational_events
from generation.hallucination import guard_answer
from generation.intent import classify_intent
from generation.llm_client import OllamaGenerationClient
from generation.prompt_builder import (
    PromptBundle,
    build_conversational_prompt,
    build_prompt,
    fallback_answer,
)
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

    with stage("intent_classify"):
        intent_result = classify_intent(request.message)

    if intent_result.is_conversational:
        logger.info(
            "chat_retrieval_bypassed",
            intent=intent_result.intent.value,
            matched_rule=intent_result.matched_rule,
            session_id=request.session_id,
        )
        with stage("prompt_build"):
            return build_conversational_prompt(
                request.message,
                intent=intent_result.intent,
                recent_history=recent_history,
            )

    with stage("retriever_init"):
        retriever = Retriever()
    try:
        retrieved = await retriever.retrieve(
            request.message,
            filters=request.filters,
            top_k=request.top_k,
        )
    finally:
        with stage("retriever_close"):
            await retriever.close()

    with stage("prompt_build"):
        return build_prompt(request.message, retrieved.candidates, recent_history=recent_history)


def _skip_generation(prompt: PromptBundle) -> bool:
    """Whether this turn can be answered from a template instead of the LLM.

    Measured on a 4 vCPU VPS: generating a greeting costs ~5s and evicts the
    knowledge prompt from Ollama's single KV cache slot, which then forces a
    full prefill on the next real question. Templating greetings removes both
    costs. Set CONVERSATIONAL_USE_LLM=true to generate them instead.
    """

    return prompt.intent.is_conversational and not get_settings().conversational_use_llm


async def _templated_conversational_response(
    request: ChatRequest,
    memory: SessionMemory,
    prompt: PromptBundle,
) -> ChatResponse:
    """Answer a greeting from a template, with no LLM round trip."""

    with stage("templated_response"):
        answer = fallback_answer(prompt.intent)
    logger.info("conversational_templated", intent=prompt.intent.value)
    with stage("session_memory_write"):
        await memory.add_turn(request.session_id, request.message, answer)
    with stage("response_serialize"):
        return ChatResponse(
            answer=answer,
            confidence=1.0,
            sources=[],
            session_id=request.session_id,
            allowed=True,
            reason="conversational_templated",
            intent=prompt.intent.value,
        )


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    with request_timer("chat") as timer:
        with stage("client_init"):
            memory = SessionMemory()
        try:
            return await _chat(request, memory)
        finally:
            with stage("client_close"):
                await memory.close()
            timer.log("chat_timing", session_id=request.session_id)


async def _chat(request: ChatRequest, memory: SessionMemory) -> ChatResponse:
        with stage("session_memory_read"):
            history = await memory.format_recent_history(request.session_id)
        prompt = await build_turn_prompt(request, recent_history=history)

        # Templated turns never construct an LLM client, so a greeting costs no
        # Ollama connection setup and no generation round trip.
        if _skip_generation(prompt):
            return await _templated_conversational_response(request, memory, prompt)

        with stage("llm_client_init"):
            llm = OllamaGenerationClient()
        answer_parts: list[str] = []
        generation_started = time.perf_counter()
        first_token_seen = False
        try:
            async for chunk in llm.stream_generate(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
            ):
                if chunk.token:
                    if not first_token_seen:
                        mark("llm_time_to_first_token", generation_started)
                        first_token_seen = True
                    answer_parts.append(chunk.token)
                if chunk.done:
                    break
            mark("llm_total_generation", generation_started)
        except ExternalServiceError:
            # A knowledge query still surfaces 503 so the caller can retry an
            # infrastructure outage. A greeting has no dependency on retrieval
            # or sources, so it degrades to a friendly reply instead of failing.
            if not prompt.intent.is_conversational:
                raise
            logger.warning("conversational_generation_unavailable", intent=prompt.intent.value)
            answer_parts = []
        finally:
            with stage("llm_client_close"):
                await llm.close()
        with stage("guardrails"):
            guarded = guard_answer("".join(answer_parts), prompt.source_map, intent=prompt.intent)
        with stage("session_memory_write"):
            await memory.add_turn(request.session_id, request.message, guarded.answer)
        with stage("response_serialize"):
            return ChatResponse(
                answer=guarded.answer,
                confidence=guarded.confidence,
                sources=[] if prompt.intent.is_conversational else guarded.citation_validation.sources,
                session_id=request.session_id,
                allowed=guarded.allowed,
                reason=guarded.reason,
                intent=prompt.intent.value,
            )


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def event_stream():
        with request_timer("chat_stream") as timer:
            with stage("client_init"):
                memory = SessionMemory()
                streamer = StreamingAnswerGenerator()
            try:
                with stage("session_memory_read"):
                    history = await memory.format_recent_history(request.session_id)
                prompt = await build_turn_prompt(request, recent_history=history)

                if _skip_generation(prompt):
                    answer = fallback_answer(prompt.intent)
                    logger.info("conversational_templated", intent=prompt.intent.value)
                    for event in templated_conversational_events(answer, prompt.intent):
                        yield event
                    with stage("session_memory_write"):
                        await memory.add_turn(request.session_id, request.message, answer)
                    return

                final_answer = None
                stream_started = time.perf_counter()
                first_event_seen = False
                async for event, result in streamer.stream_sse_with_result(prompt):
                    if not first_event_seen:
                        mark("sse_time_to_first_event", stream_started)
                        first_event_seen = True
                    if result is not None:
                        final_answer = result.answer
                    yield event
                mark("sse_total_stream", stream_started)
                if final_answer:
                    with stage("session_memory_write"):
                        await memory.add_turn(request.session_id, request.message, final_answer)
            finally:
                with stage("client_close"):
                    await memory.close()
                    await streamer.close()
                timer.log("chat_stream_timing", session_id=request.session_id)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
