from __future__ import annotations

from collections import defaultdict

from retrieval.types import RetrievalCandidate


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievalCandidate]],
    *,
    top_k: int,
    rrf_k: int = 60,
) -> list[RetrievalCandidate]:
    """Fuse ranked candidate lists using Reciprocal Rank Fusion."""

    scores: dict[str, float] = defaultdict(float)
    best: dict[str, RetrievalCandidate] = {}

    for candidates in result_lists:
        for rank, candidate in enumerate(candidates, start=1):
            scores[candidate.chunk_id] += 1.0 / (rrf_k + rank)
            if candidate.chunk_id not in best or candidate.score > best[candidate.chunk_id].score:
                best[candidate.chunk_id] = candidate

    fused = sorted(best.values(), key=lambda item: scores[item.chunk_id], reverse=True)
    output: list[RetrievalCandidate] = []
    for index, candidate in enumerate(fused[:top_k], start=1):
        output.append(
            RetrievalCandidate(
                chunk_id=candidate.chunk_id,
                document_id=candidate.document_id,
                content=candidate.content,
                metadata=candidate.metadata,
                score=scores[candidate.chunk_id],
                rank=index,
                retrieval_type="hybrid_rrf",
            )
        )
    return output
