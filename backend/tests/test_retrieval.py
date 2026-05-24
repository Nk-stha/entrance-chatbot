import httpx
import pytest

from config import Settings
from models.domain import SourceType
from retrieval.hybrid import reciprocal_rank_fusion
from retrieval.query_rewriter import QueryRewriter
from retrieval.retriever import Retriever, apply_intent_relevance_filter, apply_minimum_relevance_filter, lexical_relevance_score
from retrieval.types import RetrievalCandidate, RetrievalFilters


def settings() -> Settings:
    return Settings(
        BACKEND_API_BASE_URL="https://api.entrancegateway.com/api/v1",
        CHATBOT_BACKEND_JWT="test.jwt.token",
        API_KEY="test-admin-api-key",
        RETRIEVAL_TOP_K=3,
    )


@pytest.mark.asyncio
async def test_query_rewriter_returns_rewritten_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "BCA colleges in Kathmandu"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama.test") as client:
        rewriter = QueryRewriter(settings=settings(), http_client=client)
        assert await rewriter.rewrite("Where can I study BCA?") == "BCA colleges in Kathmandu"


@pytest.mark.asyncio
async def test_query_rewriter_falls_back_on_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "failed"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama.test") as client:
        rewriter = QueryRewriter(settings=settings(), http_client=client)
        assert await rewriter.rewrite("BCA course") == "BCA course"


def test_retrieval_filters_to_chroma_where() -> None:
    filters = RetrievalFilters(source_type=SourceType.COURSE, source_id="course:8", category="course")
    assert filters.to_chroma_where() == {
        "$and": [
            {"source_type": "course"},
            {"source_id": "course:8"},
            {"category": "course"},
        ]
    }


def candidate(
    chunk_id: str,
    rank: int,
    score: float,
    retrieval_type: str,
    *,
    content: str | None = None,
    title: str = "BCA",
    source_type: str = "course",
) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id=chunk_id.split(":chunk", 1)[0],
        content=content or f"content {chunk_id}",
        metadata={"source_type": source_type, "source_id": chunk_id.split(":chunk", 1)[0], "title": title},
        score=score,
        rank=rank,
        retrieval_type=retrieval_type,
    )


def test_rrf_fuses_and_deduplicates_by_chunk_id() -> None:
    dense = [candidate("course:8:chunk:0", 1, 0.9, "dense"), candidate("course:9:chunk:0", 2, 0.8, "dense")]
    keyword = [candidate("course:8:chunk:0", 1, 2.0, "keyword"), candidate("course:7:chunk:0", 2, 1.0, "keyword")]

    fused = reciprocal_rank_fusion([dense, keyword], top_k=3)

    assert [item.chunk_id for item in fused] == ["course:8:chunk:0", "course:9:chunk:0", "course:7:chunk:0"]
    assert fused[0].retrieval_type == "hybrid_rrf"
    assert fused[0].rank == 1


def test_intent_relevance_filter_removes_business_course_for_computer_query() -> None:
    candidates = [
        candidate(
            "course:9:chunk:0",
            1,
            0.9,
            "hybrid_rrf",
            title="BBS",
            content="Course: BBS. Description: Bachelor in Business Studies.",
        ),
        candidate(
            "course:8:chunk:0",
            2,
            0.8,
            "hybrid_rrf",
            title="BCA",
            content="Course: BCA. Description: Bachelor in Computer Application.",
        ),
        candidate(
            "training:spring:chunk:0",
            3,
            0.7,
            "hybrid_rrf",
            title="Spring Boot Training",
            source_type="training",
            content="Training: Spring Boot with Spring Security and Redis caching.",
        ),
    ]

    filtered = apply_intent_relevance_filter("Which computer-related courses and trainings are available?", candidates)

    assert [item.title for item in filtered] == ["BCA", "Spring Boot Training"]


def test_minimum_relevance_filter_blocks_unrelated_training_query() -> None:
    spring_boot = candidate(
        "training:spring:chunk:0",
        1,
        0.9,
        "hybrid_rrf",
        title="Spring Boot Training",
        source_type="training",
        content="Training: Spring Boot with Spring Security and Redis caching.",
    )

    assert lexical_relevance_score("Which training teaches hacking stuff?", spring_boot) == 0.0
    assert apply_minimum_relevance_filter("Which training teaches hacking stuff?", [spring_boot], min_score=0.15) == []


def test_minimum_relevance_filter_keeps_matching_training_query() -> None:
    spring_boot = candidate(
        "training:spring:chunk:0",
        1,
        0.9,
        "hybrid_rrf",
        title="Spring Boot Training",
        source_type="training",
        content="Training: Spring Boot with Spring Security and Redis caching.",
    )

    assert lexical_relevance_score("Which training teaches Redis caching?", spring_boot) >= 0.15
    assert apply_minimum_relevance_filter("Which training teaches Redis caching?", [spring_boot], min_score=0.15) == [spring_boot]


def test_intent_relevance_filter_keeps_general_course_query_unchanged() -> None:
    candidates = [
        candidate("course:9:chunk:0", 1, 0.9, "hybrid_rrf", title="BBS", content="Course: BBS. Business Studies."),
        candidate("course:8:chunk:0", 2, 0.8, "hybrid_rrf", title="BCA", content="Course: BCA. Computer Application."),
    ]

    filtered = apply_intent_relevance_filter("Which courses are available?", candidates)

    assert filtered == candidates


class FakeEmbedder:
    async def embed_text(self, text):
        return [0.1, 0.2, 0.3]

    async def close(self):
        pass


class FakeRewriter:
    async def rewrite(self, query):
        return f"rewritten {query}"

    async def close(self):
        pass


class FakeCollection:
    def __init__(self):
        self.where_seen = []

    def query(self, **kwargs):
        self.where_seen.append(kwargs.get("where"))
        return {
            "ids": [["course:8:chunk:0"]],
            "documents": [["Course: BCA. Description: Bachelor in Computer Application."]],
            "metadatas": [[{"source_type": "course", "source_id": "course:8", "document_id": "course:8", "title": "BCA"}]],
            "distances": [[0.2]],
        }

    def get(self, **kwargs):
        self.where_seen.append(kwargs.get("where"))
        return {
            "ids": ["course:8:chunk:0", "college:1:chunk:0"],
            "documents": ["Course: BCA. Bachelor in Computer Application.", "College: ABC."],
            "metadatas": [
                {"source_type": "course", "source_id": "course:8", "document_id": "course:8", "title": "BCA"},
                {"source_type": "college", "source_id": "college:1", "document_id": "college:1", "title": "ABC"},
            ],
        }


class FakeVectorStore:
    def __init__(self):
        self.collection = FakeCollection()

    def get_collection(self):
        return self.collection


@pytest.mark.asyncio
async def test_retriever_returns_fused_results_with_filters() -> None:
    vector_store = FakeVectorStore()
    retriever = Retriever(
        settings=settings(),
        embedder=FakeEmbedder(),
        vector_store=vector_store,
        query_rewriter=FakeRewriter(),
    )

    result = await retriever.retrieve(
        "BCA course",
        filters=RetrievalFilters(source_type=SourceType.COURSE),
        top_k=3,
    )

    assert result.query == "BCA course"
    assert result.rewritten_query == "rewritten BCA course"
    assert result.candidates[0].chunk_id == "course:8:chunk:0"
    assert result.candidates[0].source_id == "course:8"
    assert vector_store.collection.where_seen == [{"source_type": "course"}, {"source_type": "course"}]


def test_keyword_search_scores_matching_documents() -> None:
    retriever = Retriever(
        settings=settings(),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
        query_rewriter=FakeRewriter(),
    )
    results = retriever.keyword_search("BCA application", top_k=3)
    assert len(results) == 1
    assert results[0].chunk_id == "course:8:chunk:0"
    assert results[0].score == 2.0
