from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from api.admin import router as admin_router
from api.chat import router as chat_router
from api.webhooks import router as webhooks_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(admin_router)
router.include_router(webhooks_router)


@router.get("/metrics", response_class=PlainTextResponse, tags=["monitoring"])
async def metrics() -> str:
    return "entrance_chatbot_up 1\n"
