from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import redis.asyncio as redis
import structlog.contextvars
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to every request and response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log request method/path/status/duration in a structured format."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Response-Time-MS"] = str(duration_ms)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple Redis-backed fixed-window rate limiter."""

    def __init__(self, app, *, redis_client=None, limit: int | None = None, window_seconds: int | None = None) -> None:
        super().__init__(app)
        settings = get_settings()
        self.limit = limit or settings.rate_limit_requests
        self.window_seconds = window_seconds or settings.rate_limit_window
        self.redis = redis_client or redis.from_url(settings.redis_url, decode_responses=True)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path.endswith("/health") or request.url.path.endswith("/readiness"):
            return await call_next(request)

        identifier = request.client.host if request.client else "unknown"
        bucket = int(time.time() // self.window_seconds)
        key = f"rag:rate:{identifier}:{bucket}"

        try:
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, self.window_seconds)
            if count > self.limit:
                logger.warning("rate_limit_exceeded", identifier=identifier, path=request.url.path, count=count)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "error": {
                            "code": "rate_limit_exceeded",
                            "message": "Too many requests. Please try again later.",
                            "request_id": getattr(request.state, "request_id", None),
                        },
                    },
                    headers={"Retry-After": str(self.window_seconds)},
                )
        except Exception as exc:
            logger.warning("rate_limit_unavailable", error=str(exc))

        return await call_next(request)


def add_core_middleware(app) -> None:
    """Register project middleware in dependency-safe order."""

    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIDMiddleware)
