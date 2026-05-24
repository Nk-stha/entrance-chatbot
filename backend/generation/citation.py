from __future__ import annotations

import re
from dataclasses import dataclass

from core.logging import get_logger
from retrieval.types import RetrievalCandidate

logger = get_logger(__name__)

_CITATION_PATTERN = re.compile(r"\[(\d+)]")


@dataclass(slots=True)
class CitationValidationResult:
    """Citation extraction and validation result."""

    cited_source_numbers: list[int]
    invalid_source_numbers: list[int]
    missing_citations: bool
    sources: list[dict[str, str]]

    @property
    def valid(self) -> bool:
        return not self.invalid_source_numbers and not self.missing_citations


def extract_citation_numbers(answer: str) -> list[int]:
    """Extract unique citation numbers from an answer in first-seen order."""

    seen: set[int] = set()
    citations: list[int] = []
    for match in _CITATION_PATTERN.finditer(answer):
        number = int(match.group(1))
        if number not in seen:
            citations.append(number)
            seen.add(number)
    return citations


def validate_citations(answer: str, source_map: dict[int, RetrievalCandidate]) -> CitationValidationResult:
    """Validate that answer citations refer only to available numbered sources."""

    cited = extract_citation_numbers(answer)
    invalid = [number for number in cited if number not in source_map]
    missing = bool(answer.strip()) and not cited
    sources = [format_source_reference(number, source_map[number]) for number in cited if number in source_map]
    logger.info(
        "citation_validation_finished",
        cited_count=len(cited),
        invalid_count=len(invalid),
        missing_citations=missing,
    )
    return CitationValidationResult(
        cited_source_numbers=cited,
        invalid_source_numbers=invalid,
        missing_citations=missing,
        sources=sources,
    )


def format_source_reference(number: int, candidate: RetrievalCandidate) -> dict[str, str]:
    """Format one retrieved candidate as a source reference."""

    return {
        "number": str(number),
        "chunk_id": candidate.chunk_id,
        "document_id": candidate.document_id,
        "source_id": candidate.source_id or "",
        "source_type": candidate.source_type or "",
        "title": candidate.title or "Untitled source",
    }
