from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from api.health import router as health_router
from api.router import router as api_router
from api.schemas import router as schemas_router
from config import get_settings
from core.exceptions import register_exception_handlers
from core.logging import configure_logging, get_logger
from core.middleware import add_core_middleware

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize lightweight shared clients for readiness checks."""

    logger.info("app_starting", environment=settings.environment)
    app.state.http_client = httpx.AsyncClient(timeout=5.0)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    yield
    logger.info("app_stopping")
    await app.state.http_client.aclose()
    await app.state.redis.aclose()


app = FastAPI(
    title="Entrance Gateway RAG Chatbot API",
    description="Backend-only RAG chatbot API for Entrance Gateway.",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_core_middleware(app)
register_exception_handlers(app)

app.include_router(health_router)
app.include_router(health_router, prefix="/api/v1")
app.include_router(schemas_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1")
