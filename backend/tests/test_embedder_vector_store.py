import httpx
import pytest

from config import Settings
from ingestion.chunker import chunk_document
from ingestion.embedder import OllamaEmbedder
from ingestion.normalizer import normalize_source
from models.domain import SourceFetchResult, SourceType
from retrieval.vector_store import VectorStore, serialize_metadata


def settings() -> Settings:
    return Settings(
        BACKEND_API_BASE_URL="https://api.entrancegateway.com/api/v1",
        CHATBOT_BACKEND_JWT="test.jwt.token",
        API_KEY="test-admin-api-key",
        CHUNK_SIZE_CHARS=120,
        CHUNK_OVERLAP_CHARS=20,
    )


def sample_chunks():
    doc = normalize_source(
        SourceFetchResult(
            source_type=SourceType.COURSE,
            source_id="course:1",
            payload={"courseId": 1, "courseName": "BCA", "description": "Computer applications"},
        )
    )
    return chunk_document(doc, settings=settings())


@pytest.mark.asyncio
async def test_ollama_embed_text_posts_expected_payload() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["json"] = request.read().decode()
        return httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://ollama.test") as http_client:
        embedder = OllamaEmbedder(settings=settings(), http_client=http_client)
        vector = await embedder.embed_text("hello")

    assert seen["path"] == "/api/embeddings"
    assert "nomic-embed-text" in seen["json"]
    assert vector == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_ollama_embed_text_rejects_empty_text() -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200))) as http_client:
        embedder = OllamaEmbedder(settings=settings(), http_client=http_client)
        with pytest.raises(ValueError, match="text must not be empty"):
            await embedder.embed_text("  ")


@pytest.mark.asyncio
async def test_embed_texts_batches_in_order() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.read().decode())
        return httpx.Response(200, json={"embedding": [float(len(calls))]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://ollama.test") as http_client:
        embedder = OllamaEmbedder(settings=settings(), http_client=http_client)
        vectors = await embedder.embed_texts(["a", "b", "c"], batch_size=2)

    assert vectors == [[1.0], [2.0], [3.0]]
    assert len(calls) == 3


def test_serialize_metadata_uses_chroma_scalars() -> None:
    chunk = sample_chunks()[0]
    metadata = serialize_metadata(chunk)
    assert metadata["source_type"] == "course"
    assert metadata["source_id"] == "course:1"
    assert metadata["document_id"] == "course:1"
    assert metadata["chunk_id"] == chunk.id
    assert isinstance(metadata["chunk_index"], int)
    assert all(value is not None for value in metadata.values())


class FakeCollection:
    def __init__(self) -> None:
        self.upserts = []
        self.deletes = []
        self._count = 0

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)
        self._count = len(kwargs["ids"])

    def delete(self, **kwargs):
        self.deletes.append(kwargs)

    def count(self):
        return self._count


class FakeChromaClient:
    def __init__(self) -> None:
        self.collection = FakeCollection()
        self.collection_args = []

    def get_or_create_collection(self, name, metadata=None):
        self.collection_args.append({"name": name, "metadata": metadata})
        return self.collection


def test_vector_store_upsert_delete_and_stats() -> None:
    fake = FakeChromaClient()
    store = VectorStore(settings=settings(), client=fake)
    chunks = sample_chunks()
    embeddings = [[0.1, 0.2, 0.3] for _ in chunks]

    assert store.upsert_chunks(chunks, embeddings) == len(chunks)
    assert fake.collection_args[0]["metadata"] == {"hnsw:space": "cosine"}
    upsert = fake.collection.upserts[0]
    assert upsert["ids"] == [chunk.id for chunk in chunks]
    assert upsert["documents"] == [chunk.content for chunk in chunks]
    assert upsert["embeddings"] == embeddings
    assert upsert["metadatas"][0]["source_id"] == "course:1"

    store.delete_by_source_id("course:1")
    store.delete_by_document_id("course:1")
    assert fake.collection.deletes == [{"where": {"source_id": "course:1"}}, {"where": {"document_id": "course:1"}}]
    assert store.stats()["count"] == len(chunks)


def test_vector_store_upsert_validates_lengths() -> None:
    store = VectorStore(settings=settings(), client=FakeChromaClient())
    with pytest.raises(ValueError, match="length mismatch"):
        store.upsert_chunks(sample_chunks(), [])
