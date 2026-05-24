from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

import redis.asyncio as redis

from config import Settings, get_settings
from core.logging import get_logger
from ingestion.api_client import BackendAPIClient
from ingestion.chunker import chunk_documents
from ingestion.embedder import OllamaEmbedder
from ingestion.normalizer import normalize_sources
from models.domain import SourceFetchResult, SourceType
from models.webhook import WebhookEventType, WebhookSyncRequest
from retrieval.vector_store import VectorStore

logger = get_logger(__name__)


class RedisLike(Protocol):
    async def set(self, name: str, value: str, ex: int | None = None, nx: bool = False) -> Any: ...
    async def get(self, name: str) -> Any: ...
    async def aclose(self) -> Any: ...


@dataclass
class IngestionReport:
    """Detailed report for full or incremental ingestion."""

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    source_types: list[str] = field(default_factory=list)
    fetched_count: int = 0
    normalized_count: int = 0
    chunk_count: int = 0
    embedded_count: int = 0
    upserted_count: int = 0
    deleted_count: int = 0
    skipped_count: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.errors

    def finish(self) -> "IngestionReport":
        self.finished_at = datetime.now(timezone.utc)
        return self

    def add_error(self, *, source_type: SourceType | str, error: Exception | str) -> None:
        self.errors.append({"source_type": str(source_type), "error": str(error)})

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "source_types": self.source_types,
            "fetched_count": self.fetched_count,
            "normalized_count": self.normalized_count,
            "chunk_count": self.chunk_count,
            "embedded_count": self.embedded_count,
            "upserted_count": self.upserted_count,
            "deleted_count": self.deleted_count,
            "skipped_count": self.skipped_count,
            "errors": self.errors,
        }


class IngestionPipeline:
    """Full and incremental RAG ingestion orchestration."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        api_client: BackendAPIClient | None = None,
        embedder: OllamaEmbedder | None = None,
        vector_store: VectorStore | None = None,
        redis_client: RedisLike | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.api_client = api_client or BackendAPIClient(settings=self.settings)
        self.embedder = embedder or OllamaEmbedder(settings=self.settings)
        self.vector_store = vector_store or VectorStore(settings=self.settings)
        self.redis_client = redis_client or redis.from_url(str(self.settings.redis_url), decode_responses=True)
        self._owns_api_client = api_client is None
        self._owns_embedder = embedder is None
        self._owns_redis = redis_client is None

    async def close(self) -> None:
        if self._owns_api_client:
            await self.api_client.close()
        if self._owns_embedder:
            await self.embedder.close()
        if self._owns_redis:
            await self.redis_client.aclose()

    async def run_full_sync(self, source_types: list[SourceType] | None = None) -> IngestionReport:
        selected = source_types or list(SourceType)
        report = IngestionReport(source_types=[source.value for source in selected])
        logger.info("ingestion_full_sync_started", source_types=report.source_types)

        for source_type in selected:
            try:
                fetch_results = await self.api_client.fetch_all_source(source_type)
                await self._ingest_fetch_results(fetch_results, report=report)
            except Exception as exc:
                logger.warning("ingestion_source_failed", source_type=source_type, error=str(exc))
                report.add_error(source_type=source_type, error=exc)

        logger.info("ingestion_full_sync_finished", **report.to_dict())
        return report.finish()

    async def refresh_source_type(self, source_type: SourceType) -> IngestionReport:
        """Targeted refresh for one source type."""

        return await self.run_full_sync([source_type])

    async def refresh_source_id(self, source_type: SourceType, source_id: str) -> IngestionReport:
        """Targeted refresh for one source record."""

        report = IngestionReport(source_types=[source_type.value])
        logger.info("ingestion_source_refresh_started", source_type=source_type, source_id=source_id)
        try:
            self.vector_store.delete_by_source_id(_canonical_source_id(source_type, source_id))
            report.deleted_count += 1
            fetch_result = await self.api_client.fetch_source_by_id(source_type, source_id)
            await self._ingest_fetch_results([fetch_result], report=report)
        except Exception as exc:
            logger.warning("ingestion_source_refresh_failed", source_type=source_type, source_id=source_id, error=str(exc))
            report.add_error(source_type=source_type, error=exc)
        return report.finish()

    async def handle_webhook(self, request: WebhookSyncRequest) -> IngestionReport:
        """Process Java backend content-change webhook safely and idempotently."""

        report = IngestionReport(source_types=[request.source_type.value])
        if not await self._claim_event(request.event_id):
            logger.info("ingestion_webhook_duplicate_ignored", event_id=request.event_id)
            report.skipped_count += 1
            return report.finish()

        logger.info(
            "ingestion_webhook_started",
            event_id=request.event_id,
            event_type=request.event_type,
            source_type=request.source_type,
            source_ids=request.source_ids,
        )

        try:
            if request.event_type == WebhookEventType.DELETED:
                for source_id in request.source_ids:
                    self.vector_store.delete_by_source_id(_canonical_source_id(request.source_type, source_id))
                    report.deleted_count += 1
            elif request.event_type == WebhookEventType.REFRESH:
                return await self.refresh_source_type(request.source_type)
            elif request.event_type in {WebhookEventType.CREATED, WebhookEventType.UPDATED}:
                for source_id in request.source_ids:
                    child_report = await self.refresh_source_id(request.source_type, source_id)
                    _merge_report(report, child_report)
            else:
                report.add_error(source_type=request.source_type, error=f"Unsupported event type: {request.event_type}")
        except Exception as exc:
            logger.warning("ingestion_webhook_failed", event_id=request.event_id, error=str(exc))
            report.add_error(source_type=request.source_type, error=exc)

        logger.info("ingestion_webhook_finished", event_id=request.event_id, **report.to_dict())
        return report.finish()

    async def run_nightly_reconciliation(self) -> IngestionReport:
        """Nightly 2:00 AM reconciliation entrypoint for schedulers/cron."""

        logger.info("ingestion_nightly_reconciliation_started")
        return await self.run_full_sync()

    async def schedule_nightly_reconciliation(self) -> None:
        """Simple in-process scheduler hook for nightly 2:00 AM reconciliation.

        Production deployments may replace this with cron/systemd/Kubernetes CronJob.
        """

        while True:
            now = datetime.now(timezone.utc)
            next_run = now.replace(hour=20, minute=15, second=0, microsecond=0)  # 02:00 Nepal Time = 20:15 UTC
            if next_run <= now:
                next_run = next_run + timedelta(days=1)
            await asyncio.sleep((next_run - now).total_seconds())
            await self.run_nightly_reconciliation()

    async def _ingest_fetch_results(self, fetch_results: list[SourceFetchResult], *, report: IngestionReport) -> None:
        report.fetched_count += len(fetch_results)
        if not fetch_results:
            return

        filtered_results = []
        for result in fetch_results:
            if await self._is_payload_unchanged(result):
                report.skipped_count += 1
                continue
            filtered_results.append(result)

        if not filtered_results:
            return

        documents = normalize_sources(filtered_results)
        report.normalized_count += len(documents)
        chunks = chunk_documents(documents, settings=self.settings)
        report.chunk_count += len(chunks)
        embeddings = await self.embedder.embed_chunks(chunks)
        report.embedded_count += len(embeddings)
        report.upserted_count += self.vector_store.upsert_chunks(chunks, embeddings)

        for result in filtered_results:
            await self._store_payload_hash(result)

    async def _claim_event(self, event_id: str) -> bool:
        key = f"rag:webhook:event:{event_id}"
        claimed = await self.redis_client.set(key, "processed", ex=7 * 24 * 60 * 60, nx=True)
        return bool(claimed)

    async def _is_payload_unchanged(self, result: SourceFetchResult) -> bool:
        key = _payload_hash_key(result.source_id)
        existing = await self.redis_client.get(key)
        current = _payload_md5(result.payload)
        return existing == current

    async def _store_payload_hash(self, result: SourceFetchResult) -> None:
        key = _payload_hash_key(result.source_id)
        digest = _payload_md5(result.payload)
        await self.redis_client.set(key, digest)


def _payload_md5(payload: dict[str, Any]) -> str:
    return hashlib.md5(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _payload_hash_key(source_id: str) -> str:
    return f"rag:payload_hash:{source_id}"


def _canonical_source_id(source_type: SourceType, source_id: str) -> str:
    return source_id if ":" in source_id else f"{source_type}:{source_id}"


def _merge_report(parent: IngestionReport, child: IngestionReport) -> None:
    parent.fetched_count += child.fetched_count
    parent.normalized_count += child.normalized_count
    parent.chunk_count += child.chunk_count
    parent.embedded_count += child.embedded_count
    parent.upserted_count += child.upserted_count
    parent.deleted_count += child.deleted_count
    parent.skipped_count += child.skipped_count
    parent.errors.extend(child.errors)
