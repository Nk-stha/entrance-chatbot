from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from core.logging import get_logger

logger = get_logger(__name__)


class Intent(StrEnum):
    """Conversation intent decided before any retrieval work happens."""

    GREETING = "greeting"
    SMALL_TALK = "small_talk"
    KNOWLEDGE = "knowledge"

    @property
    def is_conversational(self) -> bool:
        return self in {Intent.GREETING, Intent.SMALL_TALK}


@dataclass(slots=True)
class IntentResult:
    """Classified intent plus the rule that decided it, for log traceability."""

    intent: Intent
    matched_rule: str

    @property
    def is_conversational(self) -> bool:
        return self.intent.is_conversational


# A conversational turn is short by nature. Anything longer is treated as a
# knowledge query so that real questions can never be answered without sources.
MAX_CONVERSATIONAL_TOKENS = 6

# Politeness and address tokens carry no intent. Includes Nepali honorifics
# because the frontend audience is students in Nepal.
FILLER_TOKENS = frozenset(
    {
        "a",
        "ai",
        "bot",
        "dai",
        "didi",
        "hai",
        "just",
        "madam",
        "maam",
        "please",
        "sir",
        "the",
        "there",
        "um",
        "well",
    }
)

# Single tokens that on their own only ever mean "greeting".
GREETING_TOKENS = frozenset(
    {
        "greetings",
        "hello",
        "hey",
        "hi",
        "hii",
        "hiii",
        "hola",
        "howdy",
        "namaskar",
        "namaste",
        "sup",
        "yo",
    }
)

# Exact full-message matches after normalization and filler removal. Multi-word
# small talk is matched as whole phrases rather than loose tokens so that
# question words like "what" and "how" can never leak into the conversational
# path on their own (e.g. "what is the BCA fee" must stay a knowledge query).
GREETING_PHRASES = frozenset(
    {
        "good afternoon",
        "good day",
        "good evening",
        "good morning",
        "good mrng",
        "hi hello",
        "hey hi",
    }
)

SMALL_TALK_PHRASES = frozenset(
    {
        "are you a bot",
        "are you there",
        "bye",
        "can you help me",
        "goodbye",
        "good night",
        "how are you",
        "how are you doing",
        "how do you work",
        "nice to meet you",
        "ok",
        "okay",
        "see you",
        "thank you",
        "thanks",
        "thank you so much",
        "what are you",
        "what can you do",
        "what do you do",
        "what is your name",
        "who are you",
        "who made you",
    }
)

_PUNCTUATION_PATTERN = re.compile(r"[^\w\s]+", flags=re.UNICODE)
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_message(message: str) -> str:
    """Lowercase, drop punctuation, and collapse whitespace for matching."""

    lowered = message.strip().lower()
    without_punctuation = _PUNCTUATION_PATTERN.sub(" ", lowered)
    return _WHITESPACE_PATTERN.sub(" ", without_punctuation).strip()


def classify_intent(message: str) -> IntentResult:
    """Classify a user message before retrieval runs.

    The classifier is deliberately conservative: KNOWLEDGE is the default and a
    message only becomes conversational when *every* meaningful token is
    accounted for by known conversational vocabulary. That keeps mixed messages
    such as "hi, which colleges offer BCA?" on the grounded RAG path.

    Rule-based rather than model-based on purpose: it adds no LLM call to the
    hot path on a 4 vCPU VPS, and it is deterministic enough to unit test.
    """

    normalized = normalize_message(message)
    if not normalized:
        return _decided(Intent.KNOWLEDGE, "empty_message", message)

    tokens = normalized.split()
    if len(tokens) > MAX_CONVERSATIONAL_TOKENS:
        return _decided(Intent.KNOWLEDGE, "too_long_for_small_talk", message)

    meaningful = [token for token in tokens if token not in FILLER_TOKENS]
    if not meaningful:
        return _decided(Intent.GREETING, "filler_only", message)

    # Match phrases before and after filler removal. Matching the raw phrase
    # first lets known phrases keep words that are filler elsewhere ("are you a
    # bot"); the stripped form then catches padded variants ("hello sir").
    candidate_phrases = [normalized, " ".join(meaningful)]

    for phrase in candidate_phrases:
        if phrase in SMALL_TALK_PHRASES:
            return _decided(Intent.SMALL_TALK, "small_talk_phrase", message)

    for phrase in candidate_phrases:
        if phrase in GREETING_PHRASES:
            return _decided(Intent.GREETING, "greeting_phrase", message)

    if all(token in GREETING_TOKENS for token in meaningful):
        return _decided(Intent.GREETING, "greeting_tokens", message)

    # A greeting prefix followed by an exact small-talk phrase, e.g. "hi how are you".
    leading_greetings = 0
    for token in meaningful:
        if token not in GREETING_TOKENS:
            break
        leading_greetings += 1
    if leading_greetings:
        remainder = " ".join(meaningful[leading_greetings:])
        if remainder in SMALL_TALK_PHRASES:
            return _decided(Intent.SMALL_TALK, "greeting_then_small_talk", message)
        if remainder in GREETING_PHRASES:
            return _decided(Intent.GREETING, "compound_greeting", message)

    return _decided(Intent.KNOWLEDGE, "default_knowledge", message)


def _decided(intent: Intent, rule: str, message: str) -> IntentResult:
    logger.info(
        "intent_classified",
        intent=intent.value,
        matched_rule=rule,
        message_length=len(message),
    )
    return IntentResult(intent=intent, matched_rule=rule)
