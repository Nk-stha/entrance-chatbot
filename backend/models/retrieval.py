from enum import StrEnum

from pydantic import BaseModel, Field

from models.domain import DocumentChunk, SourceType


class RetrievalMethod(StrEnum):
    DENSE = "dense"
    KEYWORD = "keyword"
    RRF = "rrf"


class RetrievedChunk(BaseModel):
    """Chunk returned by retrieval with score and ranking information."""

    chunk: DocumentChunk
    score: float = Field(ge=0)
    rank: int = Field(ge=1)
    method: RetrievalMethod = RetrievalMethod.RRF


class RetrievalRequest(BaseModel):
    """Internal retrieval request contract."""

    query: str = Field(min_length=1, max_length=2000)
    source_types: list[SourceType] | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievalResult(BaseModel):
    """Internal retrieval result contract."""

    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
