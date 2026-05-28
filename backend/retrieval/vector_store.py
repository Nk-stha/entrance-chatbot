from __future__ import annotations

from typing import Any, Protocol

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings

from config import Settings, get_settings
from core.exceptions import ExternalServiceError
from core.logging import get_logger
from models.domain import DocumentChunk, SourceType

logger = get_logger(__name__)


class ChromaClientProtocol(Protocol):
    def get_or_create_collection(self, name: str, metadata: dict[str, Any] | None = None) -> Collection: ...


class VectorStore:
    """ChromaDB vector-store wrapper for RAG chunks."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: ChromaClientProtocol | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or chromadb.HttpClient(
            host=self._chroma_host,
            port=self._chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    @property
    def _chroma_host(self) -> str:
        return self.settings.chroma_base_url.replace("http://", "").replace("https://", "").split(":")[0]

    @property
    def _chroma_port(self) -> int:
        if ":" not in self.settings.chroma_base_url.replace("http://", "").replace("https://", ""):
            return 8000
        return int(self.settings.chroma_base_url.rsplit(":", 1)[1])

    def get_collection(self) -> Collection:
        """Get or create the collection using cosine distance metadata."""

        return self.client.get_or_create_collection(
            name=self.settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> int:
        """Idempotently upsert chunks and externally generated embeddings."""

        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        if not chunks:
            return 0

        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [serialize_metadata(chunk) for chunk in chunks]

        try:
            collection = self.get_collection()
            collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
            logger.info("chroma_chunks_upserted", count=len(chunks), collection=self.settings.chroma_collection)
            return len(chunks)
        except Exception as exc:
            logger.warning("chroma_chunks_upsert_failed", count=len(chunks), error=str(exc))
            raise ExternalServiceError("ChromaDB chunk upsert failed") from exc

    def get_clusters(self, chunks: list[DocumentChunk], embeddings: list[list[float]], n_neighbors: int = 5) -> list[list[DocumentChunk]]:
        """Get clusters of similar chunks from the vector store."""

        if not chunks:
            return []

        collection = self.get_collection()
        query_embeddings = embeddings
        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=n_neighbors,
            include=["documents", "metadatas"],
        )

        clusters = []
        for result in results["metadatas"]:
            cluster = []
            for metadata in result:
                chunk = DocumentChunk(
                    id=metadata["chunk_id"],
                    document_id=metadata["document_id"],
                    content=metadata["content"],
                    metadata=metadata,
                )
                cluster.append(chunk)
            clusters.append(cluster)

        return clusters

    def delete_by_source_id(self, source_id: str) -> None:
        """Delete all chunks for a source id."""

        if not source_id:
            raise ValueError("source_id must not be empty")
        try:
            self.get_collection().delete(where={"source_id": source_id})
            logger.info("chroma_source_deleted", source_id=source_id)
        except Exception as exc:
            logger.warning("chroma_source_delete_failed", source_id=source_id, error=str(exc))
            raise ExternalServiceError("ChromaDB source delete failed") from exc

    def delete_by_document_id(self, document_id: str) -> None:
        """Delete all chunks for a normalized document id."""

        if not document_id:
            raise ValueError("document_id must not be empty")
        try:
            self.get_collection().delete(where={"document_id": document_id})
            logger.info("chroma_document_deleted", document_id=document_id)
        except Exception as exc:
            logger.warning("chroma_document_delete_failed", document_id=document_id, error=str(exc))
            raise ExternalServiceError("ChromaDB document delete failed") from exc

    def stats(self) -> dict[str, Any]:
        """Return collection statistics."""

        try:
            collection = self.get_collection()
            return {
                "collection": self.settings.chroma_collection,
                "count": collection.count(),
            }
        except Exception as exc:
            logger.warning("chroma_stats_failed", error=str(exc))
            raise ExternalServiceError("ChromaDB stats failed") from exc


def serialize_metadata(chunk: DocumentChunk) -> dict[str, str | int | float | bool]:
    """Serialize Pydantic metadata into Chroma-compatible scalar values."""

    raw = chunk.metadata.model_dump(mode="json")
    output: dict[str, str | int | float | bool] = {}
    for key, value in raw.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            output[key] = value
        elif isinstance(value, SourceType):
            output[key] = value.value
        else:
            output[key] = str(value)
    output["chunk_id"] = chunk.id
    output["document_id"] = chunk.document_id
    return output