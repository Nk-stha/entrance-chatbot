import pytest

from generation.citation import extract_citation_numbers, validate_citations
from generation.hallucination import guard_answer, score_confidence
from generation.prompt_builder import REFUSAL_MESSAGE, build_prompt, format_numbered_sources
from retrieval.types import RetrievalCandidate


def candidate(chunk_id: str, score: float = 0.8) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id=chunk_id.split(":chunk", 1)[0],
        content="Course: BCA. Description: Bachelor in Computer Application.",
        metadata={"source_type": "course", "source_id": "course:8", "title": "BCA"},
        score=score,
        rank=1,
        retrieval_type="rrf_final",
    )


def test_format_numbered_sources_contains_traceability() -> None:
    text = format_numbered_sources([candidate("course:8:chunk:0")])
    assert "[1] Title: BCA (course)" in text
    assert "Source ID:" not in text
    assert "Chunk ID:" not in text
    assert "Bachelor in Computer Application" in text


def test_build_prompt_has_strict_context_only_instructions() -> None:
    bundle = build_prompt("What is BCA?", [candidate("course:8:chunk:0")])

    # Grounding rules live in the system prompt.
    assert "Answer the user's question using the numbered sources given in <context>" in bundle.system_prompt
    assert "GROUND YOUR ANSWER" in bundle.system_prompt
    assert "CITATIONS" in bundle.system_prompt
    assert "STAY ON TARGET" in bundle.system_prompt
    assert "do not describe a business course as computer-related" in bundle.system_prompt
    assert REFUSAL_MESSAGE in bundle.system_prompt

    # The user prompt carries variable content only.
    assert "<context>" in bundle.user_prompt
    assert "<question>" in bundle.user_prompt
    assert "[1] Title: BCA (course)" in bundle.user_prompt
    assert bundle.source_map[1].chunk_id == "course:8:chunk:0"


def test_build_prompt_states_refusal_rule_exactly_once() -> None:
    """Eight competing refusal directives made a 3B model refuse valid context."""

    bundle = build_prompt("What is BCA?", [candidate("course:8:chunk:0")])

    assert bundle.system_prompt.count(REFUSAL_MESSAGE) == 1
    assert REFUSAL_MESSAGE not in bundle.user_prompt


def test_build_prompt_keeps_bulk_instructions_out_of_the_variable_prompt() -> None:
    """Bulk instructions belong in the cached system prefix.

    One short citation reminder stays in the user prompt on purpose: with the
    citation rule only in the distant system prompt, the model omitted citations
    on 5/5 runs and every answer was rejected by the citation guardrail. The
    reminder is kept to a single line so prefill cost stays negligible.
    """

    bundle = build_prompt("What is BCA?", [candidate("course:8:chunk:0")])
    second = build_prompt(
        "What is BCA?", [candidate("course:8:chunk:0"), candidate("course:9:chunk:0")]
    )

    assert bundle.system_prompt == second.system_prompt
    # The trailing reminder is one line, not the old ten-bullet instruction block.
    trailing = bundle.user_prompt.split("</question>")[-1].strip()
    assert trailing.count("\n") == 0
    assert len(trailing) < 200


def test_build_prompt_validates_input() -> None:
    with pytest.raises(ValueError, match="query"):
        build_prompt(" ", [])
    with pytest.raises(ValueError, match="max_sources"):
        build_prompt("question", [], max_sources=0)


def test_extract_citation_numbers_unique_in_order() -> None:
    assert extract_citation_numbers("BCA is a course [2]. See also [1] and [2].") == [2, 1]


def test_validate_citations_detects_valid_invalid_and_missing() -> None:
    source_map = {1: candidate("course:8:chunk:0")}
    valid = validate_citations("BCA is Computer Application [1].", source_map)
    assert valid.valid is True
    assert valid.sources[0]["title"] == "BCA"

    invalid = validate_citations("BCA is Computer Application [2].", source_map)
    assert invalid.valid is False
    assert invalid.invalid_source_numbers == [2]

    missing = validate_citations("BCA is Computer Application.", source_map)
    assert missing.valid is False
    assert missing.missing_citations is True


def test_guard_answer_allows_grounded_cited_answer() -> None:
    source_map = {1: candidate("course:8:chunk:0", score=0.9)}
    result = guard_answer("BCA means Bachelor in Computer Application [1].", source_map)
    assert result.allowed is True
    assert result.reason == "grounded"
    assert result.confidence > 0.5


def test_guard_answer_refuses_missing_or_invalid_citations() -> None:
    source_map = {1: candidate("course:8:chunk:0")}
    missing = guard_answer("BCA means Bachelor in Computer Application.", source_map)
    assert missing.allowed is False
    assert missing.answer == REFUSAL_MESSAGE
    assert missing.reason == "missing_citations"

    invalid = guard_answer("BCA means Bachelor in Computer Application [9].", source_map)
    assert invalid.allowed is False
    assert invalid.answer == REFUSAL_MESSAGE
    assert invalid.reason == "invalid_citations"


def test_guard_answer_refuses_mixed_refusal_plus_answer() -> None:
    source_map = {1: candidate("course:8:chunk:0")}
    result = guard_answer(f"{REFUSAL_MESSAGE}\n\nHowever, BCA is available [1].", source_map)

    assert result.allowed is False
    assert result.answer == REFUSAL_MESSAGE
    assert result.reason == "mixed_refusal_answer"


def test_guard_answer_refuses_when_no_sources() -> None:
    result = guard_answer("BCA means Bachelor in Computer Application [1].", {})
    assert result.allowed is False
    assert result.answer == REFUSAL_MESSAGE
    assert result.confidence == 0.0
    assert result.reason == "no_sources"


def test_score_confidence_uses_valid_citations_and_scores() -> None:
    source_map = {1: candidate("course:8:chunk:0", score=0.8), 2: candidate("course:9:chunk:0", score=0.6)}
    validation = validate_citations("Answer [1][2].", source_map)
    assert score_confidence(validation, source_map) > 0.7
