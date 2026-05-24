from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from config import Settings, get_settings
from ingestion.pipeline import IngestionPipeline
from models.domain import SourceType
from retrieval.vector_store import VectorStore

router = APIRouter(prefix="/admin", tags=["admin"])


class SyncRequest(BaseModel):
    source_type: SourceType
    source_id: str | None = Field(default=None, min_length=1, max_length=256)


def verify_admin_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin API key")


@router.post("/refresh", dependencies=[Depends(verify_admin_api_key)])
async def admin_refresh() -> dict[str, object]:
    pipeline = IngestionPipeline()
    report = await pipeline.run_full_sync()
    return {"success": report.success, "report": report.to_dict()}


@router.post("/sync", dependencies=[Depends(verify_admin_api_key)])
async def admin_sync(request: SyncRequest) -> dict[str, object]:
    pipeline = IngestionPipeline()
    if request.source_id:
        report = await pipeline.refresh_source_id(request.source_type, request.source_id)
    else:
        report = await pipeline.refresh_source_type(request.source_type)
    return {"success": report.success, "report": report.to_dict()}


@router.get("/stats", dependencies=[Depends(verify_admin_api_key)])
async def admin_stats() -> dict[str, object]:
    store = VectorStore()
    return store.stats()
