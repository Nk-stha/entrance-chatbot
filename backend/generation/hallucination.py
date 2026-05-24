from __future__ import annotations

from dataclasses import dataclass

from core.logging import get_logger
from generation.citation import CitationValidationResult, validate_citations
from generation.prompt_builder import REFUSAL_MESSAGE
from retrieval.types import RetrievalCandidate

logger = get_logger(__name__)


@dataclass(slots=True)
class GuardrailResult:
    """Validated answer with confidence and citation status."""

    answer: str
    allowed: bool
    confidence: float
    reason: str
    citation_validation: CitationValidationResult


def guard_answer(answer: str, source_map: dict[int, RetrievalCandidate]) -> GuardrailResult:
    """Apply citation and context-grounding guardrails to a generated answer."""

    citation_result = validate_citations(answer, source_map)
    normalized = answer.strip()

    if not source_map:
        logger.info("hallucination_guard_refused", reason="no_sources")
        return GuardrailResult(
            answer=REFUSAL_MESSAGE,
            allowed=False,
            confidence=0.0,
            reason="no_sources",
            citation_validation=citation_result,
        )

    if not normalized:
        logger.info("hallucination_guard_refused", reason="empty_answer")
        return GuardrailResult(
            answer=REFUSAL_MESSAGE,
            allowed=False,
            confidence=0.0,
            reason="empty_answer",
            citation_validation=citation_result,
        )

    if REFUSAL_MESSAGE in normalized and normalized != REFUSAL_MESSAGE:
        logger.warning("hallucination_guard_refused", reason="mixed_refusal_answer")
        return GuardrailResult(
            answer=REFUSAL_MESSAGE,
            allowed=False,
            confidence=0.0,
            reason="mixed_refusal_answer",
            citation_validation=citation_result,
        )

    if citation_result.invalid_source_numbers:
        logger.warning("hallucination_guard_refused", reason="invalid_citations", invalid=citation_result.invalid_source_numbers)
        return GuardrailResult(
            answer=REFUSAL_MESSAGE,
            allowed=False,
            confidence=0.1,
            reason="invalid_citations",
            citation_validation=citation_result,
        )

    if citation_result.missing_citations and normalized != REFUSAL_MESSAGE:
        logger.warning("hallucination_guard_refused", reason="missing_citations")
        return GuardrailResult(
            answer=REFUSAL_MESSAGE,
            allowed=False,
            confidence=0.2,
            reason="missing_citations",
            citation_validation=citation_result,
        )

    confidence = score_confidence(citation_result, source_map)
    logger.info("hallucination_guard_allowed", confidence=confidence, citation_count=len(citation_result.cited_source_numbers))
    return GuardrailResult(
        answer=normalized,
        allowed=True,
        confidence=confidence,
        reason="grounded",
        citation_validation=citation_result,
    )


def score_confidence(citation_result: CitationValidationResult, source_map: dict[int, RetrievalCandidate]) -> float:
    """Score answer confidence from citation validity and retrieval scores."""

    if not source_map or not citation_result.valid:
        return 0.0
    cited_scores = [source_map[number].score for number in citation_result.cited_source_numbers if number in source_map]
    if not cited_scores:
        return 0.3
    avg_score = sum(cited_scores) / len(cited_scores)
    coverage_bonus = min(len(cited_scores) / max(len(source_map), 1), 1.0) * 0.25
    return round(min(1.0, 0.5 + min(avg_score, 1.0) * 0.25 + coverage_bonus), 3)
