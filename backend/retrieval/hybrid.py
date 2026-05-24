from __future__ import annotations

from retrieval.reranker import RRFReranker
from retrieval.types import RetrievalCandidate


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievalCandidate]],
    *,
    top_k: int,
    rrf_k: int = 60,
) -> list[RetrievalCandidate]:
    """Compatibility wrapper around the Phase 9 RRF reranker."""

    reranked = RRFReranker(rrf_k=rrf_k).rerank(result_lists, top_k=top_k)
    return [
        RetrievalCandidate(
            chunk_id=item.chunk_id,
            document_id=item.document_id,
            content=item.content,
            metadata=item.metadata,
            score=item.score,
            rank=item.rank,
            retrieval_type="hybrid_rrf",
        )
        for item in reranked
    ]
