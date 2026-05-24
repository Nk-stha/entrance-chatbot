from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.middleware import RateLimitMiddleware


class FakeRedisCounter:
    def __init__(self):
        self.counts = {}
        self.expirations = {}

    async def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, seconds):
        self.expirations[key] = seconds
        return True


class FailingRedisCounter:
    async def incr(self, key):
        raise RuntimeError("redis down")

    async def expire(self, key, seconds):
        raise RuntimeError("redis down")


def test_rate_limit_returns_429_after_configured_limit() -> None:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, redis_client=FakeRedisCounter(), limit=2, window_seconds=60)

    @app.get("/limited")
    async def limited():
        return {"ok": True}

    with TestClient(app) as client:
        first = client.get("/limited")
        second = client.get("/limited")
        third = client.get("/limited")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "rate_limit_exceeded"
    assert "Retry-After" in third.headers


def test_rate_limit_degrades_open_when_redis_fails() -> None:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, redis_client=FailingRedisCounter(), limit=1, window_seconds=60)

    @app.get("/limited")
    async def limited():
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/limited")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
