from __future__ import annotations

import asyncio
from typing import Any

from config import Settings, get_settings
from core.logging import get_logger
from core.timing import stage
from ingestion.embedder import OllamaEmbedder
from models.domain import DocumentChunk
from retrieval.query_rewriter import QueryRewriter
from retrieval.reranker import RRFReranker
from retrieval.types import RetrievalCandidate, RetrievalFilters, RetrievalResult
from retrieval.vector_store import VectorStore

logger = get_logger(__name__)

COMPUTER_QUERY_TERMS = {
    "computer",
    "computing",
    "programming",
    "software",
    "developer",
    "development",
    "backend",
    "frontend",
    "technology",
    "it",
    "cybersecurity",
    "cyber",
    "hacking",
    "java",
    "spring",
    "redis",
    "bca",
    "csit",
}

COMPUTER_CONTENT_TERMS = {
    "computer",
    "computing",
    "application",
    "applications",
    "science",
    "technology",
    "information technology",
    "programming",
    "software",
    "developer",
    "development",
    "backend",
    "frontend",
    "cybersecurity",
    "cyber",
    "hacking",
    "ethical hacking",
    "java",
    "spring boot",
    "spring security",
    "redis",
    "rest api",
    "rest apis",
    "bca",
    "csit",
}

COMPUTER_NEGATIVE_TERMS = {
    "business studies",
    "business",
    "management",
}


class Retriever:
    """Dense + keyword hybrid retriever over ChromaDB chunks."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        embedder: OllamaEmbedder | None = None,
        vector_store: VectorStore | None = None,
        query_rewriter: QueryRewriter | None = None,
        reranker: RRFReranker | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedder = embedder or OllamaEmbedder(settings=self.settings)
        self.vector_store = vector_store or VectorStore(settings=self.settings)
        self.query_rewriter = query_rewriter or QueryRewriter(settings=self.settings)
        self.reranker = reranker or RRFReranker(settings=self.settings)
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

        with stage("query_rewrite"):
            rewritten = await self.query_rewriter.rewrite(original)
        dense_query = rewritten if rewritten else original

        # Dense and keyword retrieval are independent, so they run concurrently.
        # Both ultimately call the synchronous ChromaDB client, which is executed
        # off the event loop so a slow vector query cannot stall other requests
        # on the single-worker VPS deployment.
        with stage("hybrid_search"):
            dense, keyword = await asyncio.gather(
                self.dense_search(dense_query, filters=filters, top_k=self.settings.retrieval_dense_top_k),
                self.keyword_search(original, filters=filters, top_k=self.settings.retrieval_keyword_top_k),
            )
        with stage("rrf_rerank"):
            fused = self.reranker.rerank([dense, keyword], top_k=max(final_top_k * 2, final_top_k))
        with stage("relevance_filters"):
            intent_filtered = apply_intent_relevance_filter(original, fused)
            threshold_filtered = apply_minimum_relevance_filter(
                original,
                intent_filtered,
                min_score=self.settings.retrieval_min_relevance_score,
            )
        output = threshold_filtered[:final_top_k]
        logger.info(
            "retrieval_finished",
            dense_count=len(dense),
            keyword_count=len(keyword),
            fused_count=len(fused),
            filtered_count=len(output),
        )
        return RetrievalResult(query=original, rewritten_query=rewritten, candidates=output)

    async def get_clusters(
        self,
        chunks: list[DocumentChunk],
        n_neighbors: int = 5,
    ) -> list[list[DocumentChunk]]:
        """Get clusters of similar chunks."""

        if not chunks:
            return []

        embeddings = await self.embedder.embed_chunks(chunks)
        return self.vector_store.get_clusters(chunks, embeddings, n_neighbors)

    async def dense_search(
        self,
        query: str,
        *,
        filters: RetrievalFilters | None = None,
        top_k: int | None = None,
    ) -> list[RetrievalCandidate]:
        with stage("embed_query"):
            vector = await self.embedder.embed_text(query)
        with stage("chroma_get_collection"):
            collection = self.vector_store.get_collection()
        with stage("chroma_query"):
            result = await asyncio.to_thread(
                lambda: collection.query(
                    query_embeddings=[vector],
                    n_results=top_k or self.settings.retrieval_dense_top_k,
                    where=filters.to_chroma_where() if filters else None,
                    include=["documents", "metadatas", "distances"],
                )
            )
        return _query_result_to_candidates(result, retrieval_type="dense")

    async def keyword_search(
        self,
        query: str,
        *,
        filters: RetrievalFilters | None = None,
        top_k: int | None = None,
    ) -> list[RetrievalCandidate]:
        """Keyword-score chunks fetched from ChromaDB.

        NOTE: this fetches the whole (optionally filtered) collection and scores
        it in Python, so its cost grows linearly with corpus size. It is fine at
        the current corpus but needs a `where_document` contains-filter or a real
        BM25 index before the collection grows large. The scan runs off the event
        loop so it cannot block other requests in the meantime.
        """

        with stage("chroma_get_collection"):
            collection = self.vector_store.get_collection()
        with stage("keyword_full_scan"):
            result = await asyncio.to_thread(
                lambda: collection.get(
                    where=filters.to_chroma_where() if filters else None,
                    include=["documents", "metadatas"],
                )
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


def apply_intent_relevance_filter(query: str, candidates: list[RetrievalCandidate]) -> list[RetrievalCandidate]:
    """Apply lightweight intent-aware filtering to avoid obvious category drift."""

    if not _is_computer_related_query(query):
        return candidates

    positive: list[RetrievalCandidate] = []
    fallback: list[RetrievalCandidate] = []
    for candidate in candidates:
        if _is_computer_related_candidate(candidate):
            positive.append(candidate)
        else:
            fallback.append(candidate)

    if not positive:
        return candidates

    for index, candidate in enumerate(positive, start=1):
        candidate.rank = index
    logger.info(
        "retrieval_intent_filter_applied",
        intent="computer_related",
        kept_count=len(positive),
        removed_count=len(fallback),
    )
    return positive


def apply_minimum_relevance_filter(
    query: str,
    candidates: list[RetrievalCandidate],
    *,
    min_score: float,
) -> list[RetrievalCandidate]:
    """Drop candidates that have too little lexical overlap with the specific user query."""

    if min_score <= 0 or not candidates:
        return candidates

    scored = [(candidate, lexical_relevance_score(query, candidate)) for candidate in candidates]
    kept = [candidate for candidate, score in scored if score >= min_score]
    if not kept:
        logger.info(
            "retrieval_min_relevance_no_results",
            min_score=min_score,
            best_score=max((score for _, score in scored), default=0.0),
        )
        return []

    for index, candidate in enumerate(kept, start=1):
        candidate.rank = index
    logger.info(
        "retrieval_min_relevance_applied",
        min_score=min_score,
        kept_count=len(kept),
        removed_count=len(candidates) - len(kept),
    )
    return kept


def lexical_relevance_score(query: str, candidate: RetrievalCandidate) -> float:
    """Compute lightweight query-to-candidate lexical relevance for threshold gating."""

    terms = _meaningful_terms(query)
    if not terms:
        return 1.0

    haystack = f"{candidate.title} {candidate.content} {candidate.metadata}".lower().replace("-", " ")
    matched = sum(1 for term in terms if term in haystack)
    score = matched / len(terms)

    if _is_broad_computer_category_query(query) and _is_computer_related_candidate(candidate):
        score = max(score, 0.5)

    return min(score, 1.0)


def _is_broad_computer_category_query(query: str) -> bool:
    normalized = query.lower().replace("-", " ")
    broad_terms = {"computer", "computing", "programming", "software", "technology", "it"}
    return any(term in normalized for term in broad_terms)


def _meaningful_terms(query: str) -> list[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "available",
        "can",
        "does",
        "for",
        "give",
        "is",
        "me",
        "of",
        "or",
        "please",
        "stuff",
        "teach",
        "teaches",
        "tell",
        "that",
        "the",
        "there",
        "training",
        "trainings",
        "what",
        "which",
        "with",
    }
    normalized = query.lower().replace("-", " ").replace("?", " ")
    terms = []
    for raw in normalized.split():
        term = raw.strip(".,:;!()[]{}\"'")
        if len(term) <= 2 or term in stopwords:
            continue
        terms.append(term)
    return terms


def _is_computer_related_query(query: str) -> bool:
    normalized = query.lower().replace("-", " ")
    return any(term in normalized for term in COMPUTER_QUERY_TERMS)


def _is_computer_related_candidate(candidate: RetrievalCandidate) -> bool:
    haystack = f"{candidate.title} {candidate.content} {candidate.metadata}".lower().replace("-", " ")
    positive = any(term in haystack for term in COMPUTER_CONTENT_TERMS)
    negative = any(term in haystack for term in COMPUTER_NEGATIVE_TERMS)
    return positive and not (negative and not positive)


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