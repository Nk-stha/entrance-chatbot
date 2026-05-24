from __future__ import annotations

import time
from collections import defaultdict

from config import Settings, get_settings
from core.logging import get_logger
from retrieval.types import RetrievalCandidate

logger = get_logger(__name__)


class RRFReranker:
    """Lightweight Reciprocal Rank Fusion reranker.

    This intentionally avoids cross-encoders or extra ML rerankers to keep VPS
    memory usage low while improving final context ordering.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        rrf_k: int = 60,
        min_score: float = 0.0,
    ) -> None:
        if rrf_k <= 0:
            raise ValueError("rrf_k must be > 0")
        if min_score < 0:
            raise ValueError("min_score must be >= 0")
        self.settings = settings or get_settings()
        self.rrf_k = rrf_k
        self.min_score = min_score

    def rerank(
        self,
        result_lists: list[list[RetrievalCandidate]],
        *,
        top_k: int | None = None,
    ) -> list[RetrievalCandidate]:
        """Merge, deduplicate, filter, and rerank candidates with RRF."""

        started = time.perf_counter()
        final_top_k = top_k or self.settings.retrieval_final_top_k
        scores: dict[str, float] = defaultdict(float)
        best_by_chunk: dict[str, RetrievalCandidate] = {}
        seen_count = 0

        for candidates in result_lists:
            for rank, candidate in enumerate(candidates, start=1):
                seen_count += 1
                if candidate.score < self.min_score:
                    continue
                scores[candidate.chunk_id] += 1.0 / (self.rrf_k + rank)
                existing = best_by_chunk.get(candidate.chunk_id)
                if existing is None or candidate.score > existing.score:
                    best_by_chunk[candidate.chunk_id] = candidate

        ordered = sorted(best_by_chunk.values(), key=lambda item: scores[item.chunk_id], reverse=True)
        output: list[RetrievalCandidate] = []
        for index, candidate in enumerate(ordered[:final_top_k], start=1):
            output.append(
                RetrievalCandidate(
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    content=candidate.content,
                    metadata=candidate.metadata,
                    score=scores[candidate.chunk_id],
                    rank=index,
                    retrieval_type="rrf_final",
                )
            )

        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        logger.info(
            "rrf_rerank_finished",
            input_count=seen_count,
            deduped_count=len(best_by_chunk),
            output_count=len(output),
            top_k=final_top_k,
            latency_ms=latency_ms,
        )
        return output
