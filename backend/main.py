from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize lightweight shared clients for readiness checks."""

    app.state.http_client = httpx.AsyncClient(timeout=5.0)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.http_client.aclose()
    await app.state.redis.aclose()


app = FastAPI(
    title="Entrance Gateway RAG Chatbot API",
    description="Backend-only RAG chatbot API for Entrance Gateway.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness probe."""

    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def ready() -> dict[str, Any]:
    """Readiness probe for Redis, ChromaDB, and Ollama."""

    checks: dict[str, Any] = {}

    try:
        pong = await app.state.redis.ping()
        checks["redis"] = {"status": "ok" if pong else "error"}
    except Exception as exc:  # pragma: no cover - depends on runtime service
        checks["redis"] = {"status": "error", "detail": str(exc)}

    try:
        response = await app.state.http_client.get(f"{settings.chroma_base_url}/api/v1/heartbeat")
        checks["chromadb"] = {"status": "ok" if response.is_success else "error"}
    except Exception as exc:  # pragma: no cover - depends on runtime service
        checks["chromadb"] = {"status": "error", "detail": str(exc)}

    try:
        response = await app.state.http_client.get(f"{settings.ollama_base_url}/api/tags")
        checks["ollama"] = {"status": "ok" if response.is_success else "error"}
    except Exception as exc:  # pragma: no cover - depends on runtime service
        checks["ollama"] = {"status": "error", "detail": str(exc)}

    is_ready = all(value.get("status") == "ok" for value in checks.values())
    return {"status": "ready" if is_ready else "not_ready", "components": checks}


@app.get("/api/v1/health", tags=["health"])
async def versioned_health() -> dict[str, str]:
    """Versioned liveness probe."""

    return await health()


@app.get("/api/v1/health/ready", tags=["health"])
async def versioned_ready() -> dict[str, Any]:
    """Versioned readiness probe."""

    return await ready()
