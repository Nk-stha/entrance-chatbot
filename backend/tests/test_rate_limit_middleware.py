from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from core.middleware import RateLimitMiddleware


class CountingRedis:
    def __init__(self) -> None:
        self.count = 0

    async def incr(self, key: str) -> int:
        self.count += 1
        return self.count

    async def expire(self, key: str, seconds: int) -> None:
        return None


def _client_with_rate_limit() -> TestClient:
    app = FastAPI()

    @app.post("/api/v1/chat")
    async def chat():
        return {"ok": True}

    @app.post("/api/v1/chat/stream")
    async def chat_stream():
        return {"ok": True}

    @app.get("/api/v1/admin/stats")
    async def admin_stats():
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, redis_client=CountingRedis(), limit=1, window_seconds=60)
    return TestClient(app)


def test_chat_endpoint_is_rate_limit_exempt() -> None:
    client = _client_with_rate_limit()

    assert client.post("/api/v1/chat").status_code == 200
    assert client.post("/api/v1/chat").status_code == 200


def test_chat_stream_endpoint_is_rate_limit_exempt() -> None:
    client = _client_with_rate_limit()

    assert client.post("/api/v1/chat/stream").status_code == 200
    assert client.post("/api/v1/chat/stream").status_code == 200


def test_non_chat_endpoint_still_rate_limited() -> None:
    client = _client_with_rate_limit()

    assert client.get("/api/v1/admin/stats").status_code == 200
    assert client.get("/api/v1/admin/stats").status_code == 429
