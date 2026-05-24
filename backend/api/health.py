from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, status

from config import get_settings
from models.schemas import ComponentHealth, HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe."""

    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=ReadinessResponse)
async def ready(request: Request) -> ReadinessResponse:
    """Readiness probe for Redis, ChromaDB, and Ollama."""

    checks: dict[str, ComponentHealth] = {}

    try:
        pong = await request.app.state.redis.ping()
        checks["redis"] = ComponentHealth(status="ok" if pong else "error")
    except Exception as exc:  # pragma: no cover - depends on runtime service
        checks["redis"] = ComponentHealth(status="error", detail=str(exc))

    try:
        response = await request.app.state.http_client.get(
            f"{settings.chroma_base_url}/api/v1/heartbeat"
        )
        checks["chromadb"] = ComponentHealth(
            status="ok" if response.is_success else "error",
            detail=None if response.is_success else response.text,
        )
    except httpx.HTTPError as exc:  # pragma: no cover - depends on runtime service
        checks["chromadb"] = ComponentHealth(status="error", detail=str(exc))

    try:
        response = await request.app.state.http_client.get(f"{settings.ollama_base_url}/api/tags")
        checks["ollama"] = ComponentHealth(
            status="ok" if response.is_success else "error",
            detail=None if response.is_success else response.text,
        )
    except httpx.HTTPError as exc:  # pragma: no cover - depends on runtime service
        checks["ollama"] = ComponentHealth(status="error", detail=str(exc))

    is_ready = all(component.status == "ok" for component in checks.values())
    return ReadinessResponse(status="ready" if is_ready else "not_ready", components=checks)


@router.get("/debug/settings", include_in_schema=False)
async def debug_settings() -> dict[str, Any]:
    """Non-secret settings snapshot for local debugging."""

    if settings.environment not in {"development", "local", "test"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    return {
        "environment": settings.environment,
        "backend_api_base_url": settings.backend_api_base_url,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "ollama_embed_model": settings.ollama_embed_model,
        "chroma_base_url": settings.chroma_base_url,
        "chroma_collection": settings.chroma_collection,
    }
