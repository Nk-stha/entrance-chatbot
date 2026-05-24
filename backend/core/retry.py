from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    initial_delay_seconds: float = 0.5,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Retry an async operation with exponential backoff."""

    delay = initial_delay_seconds
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except retryable_exceptions as exc:
            last_error = exc
            if attempt >= attempts:
                break
            logger.warning(
                "retrying_operation",
                attempt=attempt,
                attempts=attempts,
                delay_seconds=delay,
                error=str(exc),
            )
            await asyncio.sleep(delay)
            delay *= backoff_factor

    assert last_error is not None
    raise last_error
