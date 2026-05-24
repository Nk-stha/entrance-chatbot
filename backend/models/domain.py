from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class SourceType(StrEnum):
    """Supported Java backend source types for v1 ingestion."""

    COURSE = "course"
    COLLEGE = "college"
    SYLLABUS = "syllabus"
    NOTE = "note"
    OLD_QUESTION = "old_question"
    TRAINING = "training"
    QUESTION_SET = "question_set"
    QUESTION = "question"


class DocumentMetadata(BaseModel):
    """Canonical metadata attached to every normalized source document."""

    model_config = ConfigDict(extra="allow")

    source_type: SourceType
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None
    version: str | None = None
    url: HttpUrl | None = None
    payload_hash: str | None = None

    @field_validator("url", mode="before")
    @classmethod
    def empty_url_to_none(cls, value: Any) -> Any:
        """Treat empty URL strings as missing instead of bypassing URL validation."""

        if value == "":
            return None
        return value


class NormalizedDocument(BaseModel):
    """Backend-agnostic document produced after source normalization."""

    id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    metadata: DocumentMetadata
    raw: dict[str, Any] = Field(default_factory=dict)


class ChunkMetadata(DocumentMetadata):
    """Metadata attached to a text chunk stored in ChromaDB."""

    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    chunk_start: int = Field(ge=0)
    chunk_end: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_chunk_offsets(self) -> "ChunkMetadata":
        """Ensure chunk offsets describe a non-empty forward range."""

        if self.chunk_end <= self.chunk_start:
            raise ValueError("chunk_end must be greater than chunk_start")
        return self


class DocumentChunk(BaseModel):
    """Chunk of a normalized document ready for embedding and vector storage."""

    id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    metadata: ChunkMetadata


class SourceFetchResult(BaseModel):
    """Raw source API fetch result before normalization."""

    source_type: SourceType
    source_id: str = Field(min_length=1)
    payload: dict[str, Any]
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
