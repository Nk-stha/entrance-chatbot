import json

import pytest

from config import Settings
from generation.prompt_builder import build_prompt
from memory.session import ChatMessage, SessionMemory, format_messages_for_prompt
from retrieval.types import RetrievalCandidate


def settings(max_messages=4) -> Settings:
    return Settings(
        BACKEND_API_BASE_URL="https://api.entrancegateway.com/api/v1",
        CHATBOT_BACKEND_JWT="test.jwt.token",
        API_KEY="test-admin-api-key",
        SESSION_TTL_SECONDS=120,
        MAX_CHAT_HISTORY_MESSAGES=max_messages,
    )


class FakeRedis:
    def __init__(self, fail=False):
        self.store = {}
        self.expirations = {}
        self.deleted = []
        self.fail = fail

    async def get(self, name):
        if self.fail:
            raise RuntimeError("redis down")
        return self.store.get(name)

    async def set(self, name, value, ex=None):
        if self.fail:
            raise RuntimeError("redis down")
        self.store[name] = value
        self.expirations[name] = ex
        return True

    async def delete(self, name):
        if self.fail:
            raise RuntimeError("redis down")
        self.deleted.append(name)
        self.store.pop(name, None)
        return 1

    async def expire(self, name, time):
        if self.fail:
            raise RuntimeError("redis down")
        self.expirations[name] = time
        return True

    async def aclose(self):
        pass


def candidate() -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id="course:8:chunk:0",
        document_id="course:8",
        content="Course: BCA.",
        metadata={"source_type": "course", "source_id": "course:8", "title": "BCA"},
        score=0.9,
        rank=1,
        retrieval_type="rrf_final",
    )


@pytest.mark.asyncio
async def test_session_memory_stores_messages_as_json_with_ttl() -> None:
    redis = FakeRedis()
    memory = SessionMemory(settings=settings(), redis_client=redis)

    messages = await memory.append_message("s1", "user", "What is BCA?")

    assert len(messages) == 1
    key = "rag:session:s1"
    assert json.loads(redis.store[key])[0]["content"] == "What is BCA?"
    assert redis.expirations[key] == 120


@pytest.mark.asyncio
async def test_session_memory_persists_across_requests() -> None:
    redis = FakeRedis()
    memory = SessionMemory(settings=settings(), redis_client=redis)
    await memory.add_turn("s1", "What is BCA?", "BCA is Bachelor in Computer Application [1].")

    loaded = await memory.get_messages("s1")

    assert [message.role for message in loaded] == ["user", "assistant"]
    assert loaded[1].content.startswith("BCA is")


@pytest.mark.asyncio
async def test_session_memory_trims_to_max_messages() -> None:
    redis = FakeRedis()
    memory = SessionMemory(settings=settings(max_messages=3), redis_client=redis)

    for i in range(5):
        await memory.append_message("s1", "user", f"message {i}")

    loaded = await memory.get_messages("s1")
    assert [message.content for message in loaded] == ["message 2", "message 3", "message 4"]


@pytest.mark.asyncio
async def test_clear_session_deletes_key() -> None:
    redis = FakeRedis()
    memory = SessionMemory(settings=settings(), redis_client=redis)
    await memory.append_message("s1", "user", "hello")

    assert await memory.clear_session("s1") is True
    assert "rag:session:s1" in redis.deleted
    assert await memory.get_messages("s1") == []


@pytest.mark.asyncio
async def test_redis_failure_degrades_gracefully() -> None:
    memory = SessionMemory(settings=settings(), redis_client=FakeRedis(fail=True))

    assert await memory.get_messages("s1") == []
    assert await memory.clear_session("s1") is False
    messages = await memory.append_message("s1", "user", "hello")
    assert len(messages) == 1


def test_format_messages_for_prompt() -> None:
    history = format_messages_for_prompt([
        ChatMessage(role="user", content="What is BCA?"),
        ChatMessage(role="assistant", content="BCA is Bachelor in Computer Application [1]."),
    ])

    assert "User: What is BCA?" in history
    assert "Assistant: BCA is Bachelor" in history


def test_history_strips_stale_citation_markers() -> None:
    """Source numbers are per-turn: [1] last turn is a different chunk this turn.

    Leaving them in history let the model copy a previous answer verbatim and
    still pass citation validation, because the numbers exist in the new
    context too - the "asked about CSIT, got the BCA answer" bug.
    """

    history = format_messages_for_prompt([
        ChatMessage(role="user", content="what is bca semester 1 syllabus"),
        ChatMessage(
            role="assistant",
            content="BCA semester 1 includes Computer Fundamentals [1], System Analysis [2][3].",
        ),
    ])

    assert "[1]" not in history
    assert "[2]" not in history
    assert "[3]" not in history
    assert "Computer Fundamentals" in history
    # The user's own message is left untouched.
    assert "what is bca semester 1 syllabus" in history


def test_build_prompt_fences_history_away_from_context() -> None:
    prompt = build_prompt(
        "Tell me more",
        [candidate()],
        recent_history="User: What is BCA?\nAssistant: BCA is Bachelor in Computer Application.",
    )

    assert "<history>" in prompt.user_prompt
    assert "</history>" in prompt.user_prompt
    assert "Assistant: BCA is Bachelor" in prompt.user_prompt
    assert "<question>\nTell me more\n</question>" in prompt.user_prompt
    # History must be fenced off before the evidence block begins.
    assert prompt.user_prompt.index("</history>") < prompt.user_prompt.index("<context>")
    assert "never copy facts from them" in prompt.user_prompt


def test_chat_message_validates_role_and_content() -> None:
    with pytest.raises(ValueError, match="role"):
        ChatMessage(role="system", content="hello")
    with pytest.raises(ValueError, match="content"):
        ChatMessage(role="user", content=" ")
