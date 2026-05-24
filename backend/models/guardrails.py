from enum import StrEnum

from pydantic import BaseModel, Field


class GuardrailDecision(StrEnum):
    ALLOW = "allow"
    REFUSE = "refuse"
    FALLBACK = "fallback"


class GuardrailReason(StrEnum):
    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    NO_CONTEXT = "no_context"
    UNSAFE = "unsafe"
    LOW_CONFIDENCE = "low_confidence"


class GuardrailResult(BaseModel):
    """Result of a future hallucination/safety guard check."""

    decision: GuardrailDecision
    reason: GuardrailReason
    message: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class AnswerGuardResult(GuardrailResult):
    """Guard result attached to generated answers."""

    grounded: bool = True
    missing_context: list[str] = Field(default_factory=list)
