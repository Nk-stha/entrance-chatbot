from datetime import datetime, timezone

import pytest

from ingestion.pipeline import IngestionPipeline, _payload_hash_key
from models.domain import SourceFetchResult, SourceType
from models.webhook import WebhookEventType, WebhookSyncRequest


class FakeAPIClient:
    def __init__(self):
        self.fetch_all = {
            SourceType.COURSE: [SourceFetchResult(source_type=SourceType.COURSE, source_id="course:1", payload={"courseId": 1, "courseName": "BCA", "description": "Course"})],
            SourceType.NOTE: [SourceFetchResult(source_type=SourceType.NOTE, source_id="note:2", payload={"noteId": 2, "noteName": "Loops", "noteDescription": "Notes"})],
        }
        self.by_id = {
            (SourceType.COURSE, "1"): SourceFetchResult(source_type=SourceType.COURSE, source_id="course:1", payload={"courseId": 1, "courseName": "BCA Updated", "description": "Updated"})
        }

    async def fetch_all_source(self, source_type):
        if source_type == SourceType.TRAINING:
            raise RuntimeError("source failed")
        return self.fetch_all.get(source_type, [])

    async def fetch_source_by_id(self, source_type, source_id):
        raw_id = source_id.split(":", 1)[1] if ":" in source_id else source_id
        return self.by_id[(source_type, raw_id)]

    async def close(self):
        pass


class FakeEmbedder:
    async def embed_chunks(self, chunks):
        return [[float(index), 0.1, 0.2] for index, _ in enumerate(chunks)]

    async def close(self):
        pass


class FakeVectorStore:
    def __init__(self):
        self.upserts = []
        self.deleted_sources = []

    def upsert_chunks(self, chunks, embeddings):
        self.upserts.append((chunks, embeddings))
        return len(chunks)

    def delete_by_source_id(self, source_id):
        self.deleted_sources.append(source_id)


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def set(self, name, value, ex=None, nx=False):
        if nx and name in self.store:
            return False
        self.store[name] = value
        return True

    async def get(self, name):
        return self.store.get(name)

    async def aclose(self):
        pass


def make_pipeline(redis_client=None, api_client=None, vector_store=None):
    return IngestionPipeline(
        api_client=api_client or FakeAPIClient(),
        embedder=FakeEmbedder(),
        vector_store=vector_store or FakeVectorStore(),
        redis_client=redis_client or FakeRedis(),
    )


@pytest.mark.asyncio
async def test_full_sync_ingests_sources_and_reports_counts() -> None:
    vector_store = FakeVectorStore()
    pipeline = make_pipeline(vector_store=vector_store)

    report = await pipeline.run_full_sync([SourceType.COURSE, SourceType.NOTE])

    assert report.success is True
    assert report.fetched_count == 2
    assert report.normalized_count == 2
    assert report.chunk_count == 2
    assert report.embedded_count == 2
    assert report.upserted_count == 2
    assert len(vector_store.upserts) == 2


@pytest.mark.asyncio
async def test_full_sync_skips_unchanged_payload() -> None:
    redis_client = FakeRedis()
    pipeline = make_pipeline(redis_client=redis_client)
    first = await pipeline.run_full_sync([SourceType.COURSE])
    second = await pipeline.run_full_sync([SourceType.COURSE])

    assert first.upserted_count == 1
    assert second.skipped_count == 1
    assert second.upserted_count == 0
    assert _payload_hash_key("course:1") in redis_client.store


@pytest.mark.asyncio
async def test_webhook_created_refreshes_only_changed_source() -> None:
    vector_store = FakeVectorStore()
    pipeline = make_pipeline(vector_store=vector_store)
    request = WebhookSyncRequest(
        event_id="evt-1",
        event_type=WebhookEventType.CREATED,
        source_type=SourceType.COURSE,
        source_ids=["1"],
        occurred_at=datetime.now(timezone.utc),
    )

    report = await pipeline.handle_webhook(request)

    assert report.success is True
    assert vector_store.deleted_sources == ["course:1"]
    assert report.fetched_count == 1
    assert report.upserted_count == 1


@pytest.mark.asyncio
async def test_webhook_deleted_removes_chunks() -> None:
    vector_store = FakeVectorStore()
    pipeline = make_pipeline(vector_store=vector_store)
    request = WebhookSyncRequest(
        event_id="evt-del",
        event_type=WebhookEventType.DELETED,
        source_type=SourceType.NOTE,
        source_ids=["2", "note:3"],
        occurred_at=datetime.now(timezone.utc),
    )

    report = await pipeline.handle_webhook(request)

    assert report.success is True
    assert report.deleted_count == 2
    assert vector_store.deleted_sources == ["note:2", "note:3"]


@pytest.mark.asyncio
async def test_duplicate_webhook_event_is_ignored() -> None:
    redis_client = FakeRedis()
    pipeline = make_pipeline(redis_client=redis_client)
    request = WebhookSyncRequest(
        event_id="evt-dup",
        event_type=WebhookEventType.DELETED,
        source_type=SourceType.COURSE,
        source_ids=["1"],
        occurred_at=datetime.now(timezone.utc),
    )

    first = await pipeline.handle_webhook(request)
    second = await pipeline.handle_webhook(request)

    assert first.skipped_count == 0
    assert second.skipped_count == 1
    assert second.deleted_count == 0


@pytest.mark.asyncio
async def test_failed_source_is_reported_without_crashing_sync() -> None:
    pipeline = make_pipeline()
    report = await pipeline.run_full_sync([SourceType.COURSE, SourceType.TRAINING])

    assert report.success is False
    assert report.fetched_count == 1
    assert len(report.errors) == 1
    assert report.errors[0]["source_type"] == "training"
