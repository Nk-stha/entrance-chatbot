from datetime import datetime, timezone

from fastapi import APIRouter

from models.chat import ChatMessage, ChatRequest, ChatResponse, StreamChatRequest, StreamEvent
from models.domain import DocumentChunk, NormalizedDocument, SourceFetchResult
from models.guardrails import AnswerGuardResult, GuardrailDecision, GuardrailReason
from models.ingestion import IngestionResult, RefreshRequest
from models.retrieval import RetrievalRequest, RetrievalResult
from models.webhook import WebhookSyncRequest

router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.get("/phase-3", include_in_schema=False)
async def phase_3_schema_names() -> dict[str, list[str]]:
    """List Phase 3 schemas available in the OpenAPI components."""

    return {
        "schemas": [
            "SourceFetchResult",
            "NormalizedDocument",
            "DocumentChunk",
            "RetrievedChunk",
            "RetrievalRequest",
            "RetrievalResult",
            "ChatMessage",
            "ChatRequest",
            "StreamChatRequest",
            "ChatResponse",
            "StreamEvent",
            "WebhookSyncRequest",
            "RefreshRequest",
            "IngestionResult",
            "GuardrailResult",
            "AnswerGuardResult",
        ]
    }


@router.post("/examples/source-fetch", response_model=SourceFetchResult)
async def source_fetch_schema_example(payload: SourceFetchResult) -> SourceFetchResult:
    """Schema-only endpoint for validating raw source fetch contracts."""

    return payload


@router.post("/examples/document", response_model=DocumentChunk)
async def document_chunk_schema_example(payload: DocumentChunk) -> DocumentChunk:
    """Schema-only endpoint for validating document chunk contracts."""

    return payload


@router.post("/examples/normalized-document", response_model=NormalizedDocument)
async def normalized_document_schema_example(payload: NormalizedDocument) -> NormalizedDocument:
    """Schema-only endpoint for validating normalized document contracts."""

    return payload


@router.post("/examples/retrieval", response_model=RetrievalResult)
async def retrieval_schema_example(payload: RetrievalRequest) -> RetrievalResult:
    """Schema-only endpoint for validating retrieval contracts."""

    return RetrievalResult(query=payload.query)


@router.post("/examples/message", response_model=ChatMessage)
async def message_schema_example(payload: ChatMessage) -> ChatMessage:
    """Schema-only endpoint for validating chat message contracts."""

    return payload


@router.post("/examples/chat", response_model=ChatResponse)
async def chat_schema_example(payload: ChatRequest) -> ChatResponse:
    """Schema-only endpoint for validating chat request contracts."""

    return ChatResponse(answer="Schema validation only.", session_id=payload.session_id or "demo")


@router.post("/examples/chat-stream", response_model=StreamEvent)
async def stream_schema_example(payload: StreamChatRequest) -> StreamEvent:
    """Schema-only endpoint for validating stream request contracts."""

    return StreamEvent(type="done", data={"session_id": payload.session_id or "demo"})


@router.post("/examples/webhook", response_model=WebhookSyncRequest)
async def webhook_schema_example(payload: WebhookSyncRequest) -> WebhookSyncRequest:
    """Schema-only endpoint for validating webhook payload contracts."""

    return payload


@router.post("/examples/refresh", response_model=IngestionResult)
async def refresh_schema_example(payload: RefreshRequest) -> IngestionResult:
    """Schema-only endpoint for validating refresh request contracts."""

    return IngestionResult(status="skipped", started_at=datetime.now(timezone.utc))


@router.get("/examples/guardrail", response_model=AnswerGuardResult)
async def guardrail_schema_example() -> AnswerGuardResult:
    """Schema-only endpoint for validating guardrail result contracts."""

    return AnswerGuardResult(
        decision=GuardrailDecision.ALLOW,
        reason=GuardrailReason.IN_SCOPE,
        grounded=True,
    )
