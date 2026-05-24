from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

import redis.asyncio as redis

from config import Settings, get_settings
from core.logging import get_logger

logger = get_logger(__name__)


class RedisMemoryLike(Protocol):
    async def get(self, name: str) -> Any: ...
    async def set(self, name: str, value: str, ex: int | None = None) -> Any: ...
    async def delete(self, name: str) -> Any: ...
    async def expire(self, name: str, time: int) -> Any: ...
    async def aclose(self) -> Any: ...


@dataclass(slots=True)
class ChatMessage:
    """One session memory message."""

    role: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if self.role not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")
        if not self.content.strip():
            raise ValueError("content must not be empty")


class SessionMemory:
    """Redis-backed short-term conversation memory."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        redis_client: RedisMemoryLike | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.redis_client = redis_client or redis.from_url(str(self.settings.redis_url), decode_responses=True)
        self._owns_redis = redis_client is None

    async def close(self) -> None:
        if self._owns_redis:
            await self.redis_client.aclose()

    async def get_messages(self, session_id: str) -> list[ChatMessage]:
        """Return recent messages, gracefully degrading to empty list on Redis failure."""

        key = self._key(session_id)
        try:
            raw = await self.redis_client.get(key)
            if not raw:
                return []
            payload = json.loads(raw)
            messages = [ChatMessage(**item) for item in payload]
            await self.redis_client.expire(key, self.settings.session_ttl_seconds)
            return messages
        except Exception as exc:
            logger.warning("session_memory_get_failed", session_id=session_id, error=str(exc))
            return []

    async def append_message(self, session_id: str, role: str, content: str) -> list[ChatMessage]:
        """Append one message and persist a trimmed JSON list with TTL."""

        message = ChatMessage(role=role, content=content)
        messages = await self.get_messages(session_id)
        messages.append(message)
        messages = self._trim(messages)
        key = self._key(session_id)
        try:
            await self.redis_client.set(
                key,
                json.dumps([asdict(item) for item in messages], ensure_ascii=False),
                ex=self.settings.session_ttl_seconds,
            )
            logger.info("session_memory_message_appended", session_id=session_id, role=role, count=len(messages))
        except Exception as exc:
            logger.warning("session_memory_append_failed", session_id=session_id, role=role, error=str(exc))
        return messages

    async def add_turn(self, session_id: str, user_message: str, assistant_message: str) -> list[ChatMessage]:
        """Append a user/assistant turn."""

        await self.append_message(session_id, "user", user_message)
        return await self.append_message(session_id, "assistant", assistant_message)

    async def clear_session(self, session_id: str) -> bool:
        """Clear all memory for a session, returning False on Redis failure."""

        try:
            await self.redis_client.delete(self._key(session_id))
            logger.info("session_memory_cleared", session_id=session_id)
            return True
        except Exception as exc:
            logger.warning("session_memory_clear_failed", session_id=session_id, error=str(exc))
            return False

    async def format_recent_history(self, session_id: str) -> str:
        """Format recent history for prompt inclusion."""

        messages = await self.get_messages(session_id)
        return format_messages_for_prompt(messages)

    def _trim(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        max_messages = max(self.settings.max_chat_history_messages, 0)
        if max_messages == 0:
            return []
        return messages[-max_messages:]

    @staticmethod
    def _key(session_id: str) -> str:
        cleaned = session_id.strip()
        if not cleaned:
            raise ValueError("session_id must not be empty")
        return f"rag:session:{cleaned}"


def format_messages_for_prompt(messages: list[ChatMessage]) -> str:
    """Format recent messages for inclusion in a generation prompt."""

    if not messages:
        return ""
    lines = ["Recent conversation history:"]
    for message in messages:
        label = "User" if message.role == "user" else "Assistant"
        lines.append(f"{label}: {message.content}")
    return "\n".join(lines)
