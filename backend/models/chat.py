from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field

from models.domain import SourceType


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    """Request body for non-streaming chat."""

    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=128)
    filters: dict[str, str | list[str]] = Field(default_factory=dict)


class StreamChatRequest(ChatRequest):
    """Request body for SSE streaming chat."""

    stream: bool = True


class Citation(BaseModel):
    source_type: SourceType
    source_id: str
    title: str
    url: str | None = None
    chunk_id: str | None = None
    score: float | None = None


class ChatResponse(BaseModel):
    """Final non-streaming chat response."""

    answer: str
    session_id: str
    citations: list[Citation] = Field(default_factory=list)
    used_context: bool = True


class StreamEventType(StrEnum):
    TOKEN = "token"
    CITATION = "citation"
    DONE = "done"
    ERROR = "error"


class StreamEvent(BaseModel):
    """SSE event payload contract."""

    type: StreamEventType
    data: str | dict | list | None = None
