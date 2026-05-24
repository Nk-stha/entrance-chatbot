from __future__ import annotations

from typing import Any

from config import Settings, get_settings
from core.logging import get_logger
from ingestion.embedder import OllamaEmbedder
from retrieval.hybrid import reciprocal_rank_fusion
from retrieval.query_rewriter import QueryRewriter
from retrieval.types import RetrievalCandidate, RetrievalFilters, RetrievalResult
from retrieval.vector_store import VectorStore

logger = get_logger(__name__)


class Retriever:
    """Dense + keyword hybrid retriever over ChromaDB chunks."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        embedder: OllamaEmbedder | None = None,
        vector_store: VectorStore | None = None,
        query_rewriter: QueryRewriter | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedder = embedder or OllamaEmbedder(settings=self.settings)
        self.vector_store = vector_store or VectorStore(settings=self.settings)
        self.query_rewriter = query_rewriter or QueryRewriter(settings=self.settings)
        self._owns_embedder = embedder is None
        self._owns_rewriter = query_rewriter is None

    async def close(self) -> None:
        if self._owns_embedder:
            await self.embedder.close()
        if self._owns_rewriter:
            await self.query_rewriter.close()

    async def retrieve(
        self,
        query: str,
        *,
        filters: RetrievalFilters | None = None,
        top_k: int | None = None,
    ) -> RetrievalResult:
        """Rewrite, embed, retrieve dense/keyword candidates, and fuse."""

        original = query.strip()
        if not original:
            raise ValueError("query must not be empty")

        final_top_k = top_k or self.settings.retrieval_final_top_k
        logger.info("retrieval_started", query_length=len(original), top_k=final_top_k)
        rewritten = await self.query_rewriter.rewrite(original)
        dense_query = rewritten if rewritten else original
        dense = await self.dense_search(dense_query, filters=filters, top_k=self.settings.retrieval_dense_top_k)
        keyword = self.keyword_search(original, filters=filters, top_k=self.settings.retrieval_keyword_top_k)
        fused = reciprocal_rank_fusion([dense, keyword], top_k=final_top_k)
        logger.info(
            "retrieval_finished",
            dense_count=len(dense),
            keyword_count=len(keyword),
            fused_count=len(fused),
        )
        return RetrievalResult(query=original, rewritten_query=rewritten, candidates=fused)

    async def dense_search(
        self,
        query: str,
        *,
        filters: RetrievalFilters | None = None,
        top_k: int | None = None,
    ) -> list[RetrievalCandidate]:
        vector = await self.embedder.embed_text(query)
        collection = self.vector_store.get_collection()
        result = collection.query(
            query_embeddings=[vector],
            n_results=top_k or self.settings.retrieval_dense_top_k,
            where=filters.to_chroma_where() if filters else None,
            include=["documents", "metadatas", "distances"],
        )
        return _query_result_to_candidates(result, retrieval_type="dense")

    def keyword_search(
        self,
        query: str,
        *,
        filters: RetrievalFilters | None = None,
        top_k: int | None = None,
    ) -> list[RetrievalCandidate]:
        collection = self.vector_store.get_collection()
        result = collection.get(
            where=filters.to_chroma_where() if filters else None,
            include=["documents", "metadatas"],
        )
        terms = [term.lower() for term in query.split() if len(term.strip()) > 1]
        scored: list[RetrievalCandidate] = []
        for chunk_id, document, metadata in zip(result.get("ids", []), result.get("documents", []), result.get("metadatas", []), strict=False):
            haystack = f"{document} {metadata}".lower()
            score = sum(1 for term in terms if term in haystack)
            if score <= 0:
                continue
            scored.append(
                RetrievalCandidate(
                    chunk_id=chunk_id,
                    document_id=str(metadata.get("document_id", "")),
                    content=document,
                    metadata=metadata,
                    score=float(score),
                    rank=0,
                    retrieval_type="keyword",
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        output = scored[: top_k or self.settings.retrieval_keyword_top_k]
        for index, candidate in enumerate(output, start=1):
            candidate.rank = index
        return output


def _query_result_to_candidates(result: dict[str, Any], *, retrieval_type: str) -> list[RetrievalCandidate]:
    ids = result.get("ids", [[]])[0] or []
    documents = result.get("documents", [[]])[0] or []
    metadatas = result.get("metadatas", [[]])[0] or []
    distances = result.get("distances", [[]])[0] or []

    candidates: list[RetrievalCandidate] = []
    for index, (chunk_id, document, metadata, distance) in enumerate(
        zip(ids, documents, metadatas, distances, strict=False),
        start=1,
    ):
        score = 1.0 / (1.0 + float(distance))
        candidates.append(
            RetrievalCandidate(
                chunk_id=chunk_id,
                document_id=str(metadata.get("document_id", "")),
                content=document,
                metadata=metadata,
                score=score,
                rank=index,
                retrieval_type=retrieval_type,
            )
        )
    return candidates
