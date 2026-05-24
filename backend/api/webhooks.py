from __future__ import annotations

from fastapi import APIRouter, Depends

from api.admin import verify_admin_api_key
from ingestion.pipeline import IngestionPipeline
from models.webhook import WebhookSyncAccepted, WebhookSyncRequest

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/sync", response_model=WebhookSyncAccepted, dependencies=[Depends(verify_admin_api_key)])
async def webhook_sync(payload: WebhookSyncRequest) -> WebhookSyncAccepted:
    pipeline = IngestionPipeline()
    await pipeline.handle_webhook(payload)
    return WebhookSyncAccepted(
        event_id=payload.event_id,
        source_type=payload.source_type,
        source_ids=payload.source_ids,
    )
