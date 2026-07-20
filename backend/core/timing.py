from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterator

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StageTimer:
    """Wall-clock durations for the stages of a single request.

    Stage timings are the only way to tell an Ollama stall apart from a slow
    ChromaDB query once a request is in production, so the timer is designed to
    be always-on: it costs one `perf_counter()` pair per stage and emits a
    single structured log line per request.
    """

    label: str
    stages: dict[str, float] = field(default_factory=dict)
    started_at: float = field(default_factory=time.perf_counter)

    def record(self, name: str, duration_ms: float) -> None:
        """Record a stage duration, summing repeats of the same stage name."""

        self.stages[name] = round(self.stages.get(name, 0.0) + duration_ms, 3)

    @property
    def total_ms(self) -> float:
        return round((time.perf_counter() - self.started_at) * 1000, 3)

    def as_dict(self) -> dict[str, float]:
        """Stage timings plus total and unattributed overhead."""

        total = self.total_ms
        measured = sum(self.stages.values())
        return {
            **self.stages,
            "total_ms": total,
            "unattributed_ms": round(total - measured, 3),
        }

    def log(self, event: str = "request_timing", **extra: object) -> None:
        logger.info(event, label=self.label, **self.as_dict(), **extra)


_current_timer: ContextVar[StageTimer | None] = ContextVar("current_timer", default=None)


def get_timer() -> StageTimer | None:
    return _current_timer.get()


@contextmanager
def request_timer(label: str) -> Iterator[StageTimer]:
    """Bind a timer for the duration of one request."""

    timer = StageTimer(label=label)
    token = _current_timer.set(timer)
    try:
        yield timer
    finally:
        _current_timer.reset(token)


@contextmanager
def stage(name: str) -> Iterator[None]:
    """Time one pipeline stage.

    A no-op when no timer is bound, so library code can be instrumented
    unconditionally without caring whether the caller wanted timings.
    """

    timer = _current_timer.get()
    if timer is None:
        yield
        return

    started = time.perf_counter()
    try:
        yield
    finally:
        timer.record(name, (time.perf_counter() - started) * 1000)


def mark(name: str, started: float) -> None:
    """Record a stage that cannot use the context manager (e.g. streaming TTFT)."""

    timer = _current_timer.get()
    if timer is not None:
        timer.record(name, (time.perf_counter() - started) * 1000)
