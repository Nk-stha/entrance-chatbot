"""Greetings and small talk must get natural replies; facts must stay RAG-grounded.

Regression cover for the defect where every greeting returned the knowledge
refusal message because the guardrail layer applied citation rules to answers
that had no sources by design.
"""

import pytest
from unittest.mock import Mock

from fastapi.testclient import TestClient

from core.exceptions import ExternalServiceError
from generation.generator import StreamingAnswerGenerator, collect_sse_events
from generation.hallucination import guard_answer
from generation.intent import Intent, classify_intent, normalize_message
from generation.llm_client import LLMStreamChunk
from generation.prompt_builder import (
    FALLBACK_GREETING,
    REFUSAL_MESSAGE,
    build_conversational_prompt,
    build_prompt,
)
from retrieval.types import RetrievalCandidate


def candidate(score: float = 0.9) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id="course:8:chunk:0",
        document_id="course:8",
        content="Course: BCA. Description: Bachelor in Computer Application.",
        metadata={"source_type": "course", "source_id": "course:8", "title": "BCA"},
        score=score,
        rank=1,
        retrieval_type="rrf_final",
    )


class FakeLLM:
    """Minimal stand-in for OllamaGenerationClient."""

    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.system_prompts: list[str] = []

    async def stream_generate(self, *, system_prompt, user_prompt):
        self.system_prompts.append(system_prompt)
        if self.error:
            raise self.error
        yield LLMStreamChunk(token=self.text)
        yield LLMStreamChunk(token="", done=True)

    async def close(self) -> None:
        pass


# --------------------------------------------------------------------------
# Intent classification
# --------------------------------------------------------------------------

GREETINGS = [
    "hi",
    "Hi",
    "hello",
    "Hello!",
    "hey",
    "hey!!",
    "yo",
    "hiii",
    "good morning",
    "Good Morning",
    "good afternoon",
    "good evening",
    "namaste",
    "Namaste!",
    "namaskar",
    "greetings",
    "hi there",
    "hello sir",
    "hi bot",
]


@pytest.mark.parametrize("message", GREETINGS)
def test_greetings_classified_as_greeting(message: str) -> None:
    assert classify_intent(message).intent is Intent.GREETING


SMALL_TALK = [
    "how are you",
    "How are you?",
    "who are you",
    "what can you do",
    "what is your name",
    "thanks",
    "thank you",
    "bye",
    "good night",
    "are you a bot",
    "hi how are you",
    "hello who are you",
]


@pytest.mark.parametrize("message", SMALL_TALK)
def test_small_talk_classified_as_small_talk(message: str) -> None:
    assert classify_intent(message).intent is Intent.SMALL_TALK


KNOWLEDGE_QUERIES = [
    # Plain knowledge questions.
    "Which colleges offer BCA?",
    "What is the BCA syllabus?",
    "how much is the BCA fee",
    "List CSIT colleges in Kathmandu",
    "IOE entrance exam syllabus",
    # A greeting prefix must not downgrade a real question.
    "hi, which colleges offer BCA?",
    "hello, what is the CMAT exam",
    "good morning, tell me about CSIT",
    # Elliptical follow-ups belong on the grounded path.
    "tell me more",
    "and the syllabus?",
    "what about the fees",
    "any others",
    # Long messages are never conversational.
    "hi hi hi hi hi hi hi hi",
]


@pytest.mark.parametrize("message", KNOWLEDGE_QUERIES)
def test_knowledge_queries_stay_on_grounded_path(message: str) -> None:
    assert classify_intent(message).intent is Intent.KNOWLEDGE


def test_intent_defaults_to_knowledge_for_unknown_input() -> None:
    assert classify_intent("qwerty asdf").intent is Intent.KNOWLEDGE
    assert classify_intent("   ").intent is Intent.KNOWLEDGE


def test_normalize_message_strips_punctuation_and_case() -> None:
    assert normalize_message("  Good Morning!!  ") == "good morning"
    assert normalize_message("Who are you?") == "who are you"


def test_intent_result_reports_matched_rule() -> None:
    assert classify_intent("hi").matched_rule == "greeting_tokens"
    assert classify_intent("good morning").matched_rule == "greeting_phrase"
    assert classify_intent("how are you").matched_rule == "small_talk_phrase"
    assert classify_intent("Which colleges offer BCA?").matched_rule == "default_knowledge"


# --------------------------------------------------------------------------
# Conversational prompt construction
# --------------------------------------------------------------------------


def test_conversational_prompt_has_no_sources_and_forbids_citations() -> None:
    bundle = build_conversational_prompt("hi", intent=Intent.GREETING)

    assert bundle.source_map == {}
    assert bundle.intent is Intent.GREETING
    assert "NEVER include citation markers" in bundle.system_prompt
    assert "NEVER state specific facts" in bundle.system_prompt
    assert REFUSAL_MESSAGE not in bundle.system_prompt
    assert "<message>" in bundle.user_prompt


def test_conversational_prompt_rejects_knowledge_intent() -> None:
    with pytest.raises(ValueError, match="conversational intent"):
        build_conversational_prompt("Which colleges offer BCA?", intent=Intent.KNOWLEDGE)


def test_conversational_prompt_includes_recent_history() -> None:
    bundle = build_conversational_prompt(
        "how are you",
        intent=Intent.SMALL_TALK,
        recent_history="User: hi\nAssistant: Hello!",
    )
    assert "Recent history:" in bundle.user_prompt
    assert "Assistant: Hello!" in bundle.user_prompt


def test_knowledge_prompt_still_defaults_to_knowledge_intent() -> None:
    assert build_prompt("What is BCA?", [candidate()]).intent is Intent.KNOWLEDGE


# --------------------------------------------------------------------------
# Guardrails
# --------------------------------------------------------------------------


def test_guard_allows_uncited_greeting() -> None:
    """The exact defect: a natural greeting has no citations and must survive."""

    result = guard_answer("Hello! How can I help you today?", {}, intent=Intent.GREETING)

    assert result.allowed is True
    assert result.reason == "conversational"
    assert result.answer == "Hello! How can I help you today?"
    assert result.answer != REFUSAL_MESSAGE
    assert result.confidence == 1.0


def test_guard_returns_no_sources_for_conversational_turn() -> None:
    result = guard_answer("Hi there!", {}, intent=Intent.SMALL_TALK)
    assert result.citation_validation.sources == []


def test_guard_falls_back_instead_of_refusing_on_empty_greeting() -> None:
    result = guard_answer("", {}, intent=Intent.GREETING)

    assert result.allowed is True
    assert result.answer == FALLBACK_GREETING
    assert result.reason == "conversational_empty_answer"


def test_guard_replaces_refusal_parroted_on_a_greeting() -> None:
    result = guard_answer(REFUSAL_MESSAGE, {}, intent=Intent.GREETING)

    assert result.answer == FALLBACK_GREETING
    assert REFUSAL_MESSAGE not in result.answer


def test_guard_rejects_fabricated_citations_in_conversational_reply() -> None:
    result = guard_answer("Hello! BCA is offered at many colleges [1].", {}, intent=Intent.GREETING)

    assert result.answer == FALLBACK_GREETING
    assert result.reason == "conversational_fabricated_citations"


def test_knowledge_guardrails_are_unchanged() -> None:
    """The grounded path must keep refusing ungrounded answers."""

    source_map = {1: candidate()}

    assert guard_answer("BCA is Computer Application [1].", source_map).reason == "grounded"
    assert guard_answer("BCA is Computer Application.", source_map).answer == REFUSAL_MESSAGE
    assert guard_answer("BCA is Computer Application [9].", source_map).answer == REFUSAL_MESSAGE
    assert guard_answer("Anything at all.", {}).answer == REFUSAL_MESSAGE


def test_explicit_knowledge_intent_matches_default_behaviour() -> None:
    source_map = {1: candidate()}
    default = guard_answer("Uncited answer.", source_map)
    explicit = guard_answer("Uncited answer.", source_map, intent=Intent.KNOWLEDGE)
    assert default.reason == explicit.reason == "missing_citations"


# --------------------------------------------------------------------------
# Streaming
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_streaming_greeting_emits_natural_answer_and_no_sources() -> None:
    prompt = build_conversational_prompt("hi", intent=Intent.GREETING)
    generator = StreamingAnswerGenerator(llm_client=FakeLLM("Hello! How can I help?"))

    events = await collect_sse_events(generator.stream_sse(prompt))

    assert any(event.startswith("event: token") for event in events)
    sources_event = next(event for event in events if event.startswith("event: sources"))
    assert '"sources": []' in sources_event
    assert '"intent": "greeting"' in sources_event
    assert events[-1].startswith("event: done")
    assert "Hello! How can I help?" in events[-1]
    assert REFUSAL_MESSAGE not in events[-1]


@pytest.mark.asyncio
async def test_streaming_greeting_degrades_to_friendly_reply_when_llm_fails() -> None:
    prompt = build_conversational_prompt("hi", intent=Intent.GREETING)
    generator = StreamingAnswerGenerator(llm_client=FakeLLM(error=RuntimeError("ollama down")))

    events = await collect_sse_events(generator.stream_sse(prompt))

    assert events[0].startswith("event: error")
    assert FALLBACK_GREETING in events[0]
    assert REFUSAL_MESSAGE not in events[0]


@pytest.mark.asyncio
async def test_streaming_knowledge_query_still_refuses_when_llm_fails() -> None:
    prompt = build_prompt("What is BCA?", [candidate()])
    generator = StreamingAnswerGenerator(llm_client=FakeLLM(error=RuntimeError("ollama down")))

    events = await collect_sse_events(generator.stream_sse(prompt))

    assert events[0].startswith("event: error")
    assert REFUSAL_MESSAGE in events[0]


# --------------------------------------------------------------------------
# End-to-end through the API
# --------------------------------------------------------------------------


@pytest.fixture
def no_memory(monkeypatch):
    """Stub Redis-backed session memory so /chat runs without infrastructure."""

    memory = Mock()

    async def format_recent_history(_session_id):
        return ""

    async def add_turn(*_args, **_kwargs):
        return []

    async def close():
        return None

    memory.format_recent_history = format_recent_history
    memory.add_turn = add_turn
    memory.close = close
    monkeypatch.setattr("api.chat.SessionMemory", lambda: memory)
    return memory


def test_chat_greeting_bypasses_retrieval_entirely(
    api_client: TestClient, no_memory, monkeypatch
) -> None:
    def explode() -> None:
        raise AssertionError("Retriever must not be constructed for a greeting")

    monkeypatch.setattr("api.chat.Retriever", explode)
    monkeypatch.setattr("api.chat.OllamaGenerationClient", lambda: FakeLLM("Hello! How can I help?"))

    response = api_client.post("/api/v1/chat", json={"message": "hi", "session_id": "s1"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "greeting"
    assert body["allowed"] is True
    assert body["answer"] == "Hello! How can I help?"
    assert body["sources"] == []
    assert REFUSAL_MESSAGE not in body["answer"]


def test_chat_knowledge_query_runs_retrieval_and_stays_grounded(
    api_client: TestClient, no_memory, monkeypatch
) -> None:
    retriever = Mock()
    called = {"retrieve": False}

    async def retrieve(_message, filters=None, top_k=None):
        called["retrieve"] = True
        return Mock(candidates=[candidate()])

    async def close():
        return None

    retriever.retrieve = retrieve
    retriever.close = close
    monkeypatch.setattr("api.chat.Retriever", lambda: retriever)
    monkeypatch.setattr(
        "api.chat.OllamaGenerationClient",
        lambda: FakeLLM("BCA is Bachelor in Computer Application [1]."),
    )

    response = api_client.post(
        "/api/v1/chat", json={"message": "What is BCA?", "session_id": "s1"}
    )

    assert response.status_code == 200
    body = response.json()
    assert called["retrieve"] is True
    assert body["intent"] == "knowledge"
    assert body["reason"] == "grounded"
    assert body["sources"][0]["title"] == "BCA"


def test_chat_greeting_degrades_when_generation_is_unavailable(
    api_client: TestClient, no_memory, monkeypatch
) -> None:
    """A greeting must never 503; it has no dependency on retrieval or sources."""

    def explode() -> None:
        raise AssertionError("Retriever must not be constructed for a greeting")

    monkeypatch.setattr("api.chat.Retriever", explode)
    monkeypatch.setattr(
        "api.chat.OllamaGenerationClient",
        lambda: FakeLLM(error=ExternalServiceError("ollama down")),
    )

    response = api_client.post("/api/v1/chat", json={"message": "hi", "session_id": "s1"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == FALLBACK_GREETING
    assert body["intent"] == "greeting"
    assert REFUSAL_MESSAGE not in body["answer"]


def test_chat_knowledge_query_still_surfaces_outage(
    api_client: TestClient, no_memory, monkeypatch
) -> None:
    """Knowledge queries keep the 503 so callers can retry an outage."""

    retriever = Mock()

    async def retrieve(_message, filters=None, top_k=None):
        return Mock(candidates=[candidate()])

    async def close():
        return None

    retriever.retrieve = retrieve
    retriever.close = close
    monkeypatch.setattr("api.chat.Retriever", lambda: retriever)
    monkeypatch.setattr(
        "api.chat.OllamaGenerationClient",
        lambda: FakeLLM(error=ExternalServiceError("ollama down")),
    )

    response = api_client.post(
        "/api/v1/chat", json={"message": "What is BCA?", "session_id": "s1"}
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "external_service_error"


def test_chat_stream_greeting_emits_no_refusal(
    api_client: TestClient, no_memory, monkeypatch
) -> None:
    def explode() -> None:
        raise AssertionError("Retriever must not be constructed for a greeting")

    monkeypatch.setattr("api.chat.Retriever", explode)
    monkeypatch.setattr(
        "generation.generator.OllamaGenerationClient",
        lambda: FakeLLM("Hello! How can I help?"),
    )

    response = api_client.post(
        "/api/v1/chat/stream", json={"message": "hi", "session_id": "s1"}
    )

    assert response.status_code == 200
    assert "Hello! How can I help?" in response.text
    assert '"intent": "greeting"' in response.text
    assert '"sources": []' in response.text
    assert REFUSAL_MESSAGE not in response.text


def test_chat_uncited_knowledge_answer_still_refuses(
    api_client: TestClient, no_memory, monkeypatch
) -> None:
    retriever = Mock()

    async def retrieve(_message, filters=None, top_k=None):
        return Mock(candidates=[candidate()])

    async def close():
        return None

    retriever.retrieve = retrieve
    retriever.close = close
    monkeypatch.setattr("api.chat.Retriever", lambda: retriever)
    monkeypatch.setattr("api.chat.OllamaGenerationClient", lambda: FakeLLM("BCA is a degree."))

    response = api_client.post(
        "/api/v1/chat", json={"message": "What is BCA?", "session_id": "s1"}
    )

    body = response.json()
    assert body["allowed"] is False
    assert body["answer"] == REFUSAL_MESSAGE
    assert body["reason"] == "missing_citations"
