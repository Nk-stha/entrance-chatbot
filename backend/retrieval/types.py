from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.domain import SourceType


@dataclass(slots=True)
class RetrievalCandidate:
    """One retrieval candidate from dense or keyword search."""

    chunk_id: str
    document_id: str
    content: str
    metadata: dict[str, Any]
    score: float
    rank: int
    retrieval_type: str

    @property
    def source_type(self) -> str | None:
        value = self.metadata.get("source_type")
        return str(value) if value is not None else None

    @property
    def source_id(self) -> str | None:
        value = self.metadata.get("source_id")
        return str(value) if value is not None else None

    @property
    def title(self) -> str | None:
        value = self.metadata.get("title")
        return str(value) if value is not None else None


@dataclass(slots=True)
class RetrievalFilters:
    """Metadata filters for retrieval."""

    source_type: SourceType | None = None
    source_id: str | None = None
    category: str | None = None

    def to_chroma_where(self) -> dict[str, Any] | None:
        filters: list[dict[str, Any]] = []
        if self.source_type:
            filters.append({"source_type": self.source_type.value})
        if self.source_id:
            filters.append({"source_id": self.source_id})
        if self.category:
            filters.append({"category": self.category})
        if not filters:
            return None
        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}


@dataclass(slots=True)
class RetrievalResult:
    """Final fused retrieval result."""

    query: str
    rewritten_query: str
    candidates: list[RetrievalCandidate] = field(default_factory=list)
