import pytest

from config import Settings
from retrieval.reranker import RRFReranker
from retrieval.types import RetrievalCandidate


def settings() -> Settings:
    return Settings(
        BACKEND_API_BASE_URL="https://api.entrancegateway.com/api/v1",
        CHATBOT_BACKEND_JWT="test.jwt.token",
        API_KEY="test-admin-api-key",
        RETRIEVAL_FINAL_TOP_K=5,
    )


def candidate(chunk_id: str, rank: int, score: float, retrieval_type: str = "dense") -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id=chunk_id.split(":chunk", 1)[0],
        content=f"content for {chunk_id}",
        metadata={"source_type": "course", "source_id": chunk_id.split(":chunk", 1)[0], "title": chunk_id},
        score=score,
        rank=rank,
        retrieval_type=retrieval_type,
    )


def test_reranker_returns_top_5_final_context_chunks() -> None:
    dense = [candidate(f"course:{i}:chunk:0", i, 1.0 / i) for i in range(1, 8)]
    keyword = [candidate(f"course:{i}:chunk:0", i, 2.0 / i, "keyword") for i in range(1, 8)]

    output = RRFReranker(settings=settings()).rerank([dense, keyword])

    assert len(output) == 5
    assert [item.rank for item in output] == [1, 2, 3, 4, 5]
    assert all(item.retrieval_type == "rrf_final" for item in output)


def test_reranker_deduplicates_by_stable_chunk_id() -> None:
    dense = [candidate("course:8:chunk:0", 1, 0.8), candidate("course:9:chunk:0", 2, 0.7)]
    keyword = [candidate("course:8:chunk:0", 1, 3.0, "keyword")]

    output = RRFReranker(settings=settings()).rerank([dense, keyword], top_k=5)

    assert [item.chunk_id for item in output] == ["course:8:chunk:0", "course:9:chunk:0"]
    assert output[0].score > output[1].score


def test_reranker_filters_low_confidence_candidates() -> None:
    dense = [candidate("course:8:chunk:0", 1, 0.01), candidate("course:9:chunk:0", 2, 0.8)]

    output = RRFReranker(settings=settings(), min_score=0.1).rerank([dense], top_k=5)

    assert [item.chunk_id for item in output] == ["course:9:chunk:0"]


def test_reranker_validates_parameters() -> None:
    with pytest.raises(ValueError, match="rrf_k"):
        RRFReranker(settings=settings(), rrf_k=0)
    with pytest.raises(ValueError, match="min_score"):
        RRFReranker(settings=settings(), min_score=-1)
