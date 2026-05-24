from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from models.domain import SourceType


class WebhookEventType(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    REFRESH = "refresh"


class WebhookSyncRequest(BaseModel):
    """Payload sent by Java backend to trigger incremental RAG sync."""

    event_id: str = Field(min_length=1, max_length=128)
    event_type: WebhookEventType
    source_type: SourceType
    source_ids: list[str] = Field(min_length=1, max_length=500)
    occurred_at: datetime


class WebhookSyncAccepted(BaseModel):
    """Response returned once webhook payload is accepted for processing."""

    accepted: bool = True
    event_id: str
    source_type: SourceType
    source_ids: list[str]


class WebhookHeaders(BaseModel):
    """Headers required for webhook HMAC verification."""

    signature: str
    timestamp: str
