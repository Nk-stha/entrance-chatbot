from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from models.domain import SourceType


class IngestionStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class SourceIngestionStats(BaseModel):
    source_type: SourceType
    fetched: int = Field(default=0, ge=0)
    normalized: int = Field(default=0, ge=0)
    chunked: int = Field(default=0, ge=0)
    embedded: int = Field(default=0, ge=0)
    upserted: int = Field(default=0, ge=0)
    deleted: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)


class IngestionResult(BaseModel):
    status: IngestionStatus
    started_at: datetime
    completed_at: datetime | None = None
    sources: list[SourceIngestionStats] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RefreshRequest(BaseModel):
    source_types: list[SourceType] | None = None
    source_ids: list[str] | None = None
    force: bool = False


class RefreshAccepted(BaseModel):
    accepted: bool = True
    job_id: str
    source_types: list[SourceType] | None = None
    source_ids: list[str] | None = None
