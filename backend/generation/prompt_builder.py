from __future__ import annotations

from dataclasses import dataclass

from core.logging import get_logger
from retrieval.types import RetrievalCandidate

logger = get_logger(__name__)


@dataclass(slots=True)
class PromptBundle:
    """System/user prompt pair plus source lookup metadata."""

    system_prompt: str
    user_prompt: str
    source_map: dict[int, RetrievalCandidate]


REFUSAL_MESSAGE = (
    "I don't have enough verified context to answer that from the available Entrance Gateway knowledge sources."
)


SYSTEM_PROMPT = """You are the Entrance Gateway AI, an expert academic assistant for students in Nepal.
Your primary task is to answer the user's question using ONLY the provided numbered sources.

Strict Rules:
1. NO OUTSIDE KNOWLEDGE: If the sources do not contain the answer, you must reply EXACTLY: "{refusal}"
2. CITATIONS: You must cite the source for every factual claim. Place the citation at the end of the relevant sentence (e.g., [1] or [1][2]).
3. TONE & FORMAT: Be concise, encouraging, and student-friendly. Use bullet points or bold text to make the answer easy to read.
4. HALLUCINATION PREVENTION: Never invent citations. Only use the numbers provided in the context.
5. STRICT RELEVANCE GATE: If the provided sources are not strictly relevant to the user's specific request, ignore them and state you do not have the information.
6. RELEVANCE FILTERING: Retrieved sources are candidates, not automatic answers. Include only sources that directly match the user's requested category, topic, or constraint.
7. FALSE PREMISES: If the user assumes something unsupported, correct it using the sources. For example, do not call a business course computer-related unless the source says it is computer-related.""".format(refusal=REFUSAL_MESSAGE)


def build_prompt(
    query: str,
    candidates: list[RetrievalCandidate],
    *,
    max_sources: int = 5,
    recent_history: str = "",
) -> PromptBundle:
    """Build grounded system/user prompts with numbered source context."""

    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("query must not be empty")
    if max_sources <= 0:
        raise ValueError("max_sources must be > 0")

    selected = candidates[:max_sources]
    source_map = {index: candidate for index, candidate in enumerate(selected, start=1)}
    logger.info("prompt_build_started", query_length=len(cleaned_query), source_count=len(source_map))

    context = format_numbered_sources(selected)
    history_block = f"Recent history:\n{recent_history.strip()}\n" if recent_history.strip() else ""
    user_prompt = f"""{history_block}
<context>
{context if context else 'No sources available.'}
</context>

<question>
{cleaned_query}
</question>

Instructions:
- Analyze the <context> to answer the <question>.
- Do not forget to include your inline citations (e.g., [1]).
- Either answer with citations OR refuse with the exact refusal phrase; never do both in the same response.
- Include only sources that are directly relevant to the user's requested category, topic, or constraint.
- If the provided sources are not strictly relevant to the user's specific request, ignore them and use the exact refusal phrase.
- If a retrieved source is available but not relevant to the question, do not list it as an answer.
- If the user asks for computer-related options, do not include business-only sources as computer-related.
- If the <context> lacks the answer, use your exact refusal phrase.
- Format your response clearly using Markdown."""

    logger.info("prompt_build_finished", source_count=len(source_map), prompt_length=len(user_prompt))
    return PromptBundle(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, source_map=source_map)


def format_numbered_sources(candidates: list[RetrievalCandidate]) -> str:
    """Format retrieval candidates as compact numbered citation sources."""

    blocks: list[str] = []
    for index, candidate in enumerate(candidates, start=1):
        title = candidate.title or "Untitled source"
        source_type = candidate.source_type or "unknown"
        blocks.append(
            f"[{index}] Title: {title} ({source_type})\n"
            f"Content: {candidate.content.strip()}"
        )
    return "\n\n".join(blocks)
