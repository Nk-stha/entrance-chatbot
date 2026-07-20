from __future__ import annotations

from dataclasses import dataclass

from core.logging import get_logger
from generation.intent import Intent
from retrieval.types import RetrievalCandidate

logger = get_logger(__name__)


@dataclass(slots=True)
class PromptBundle:
    """System/user prompt pair plus source lookup metadata.

    `intent` travels with the bundle so that downstream generation and
    guardrail stages apply the rules matching how the prompt was built,
    instead of assuming every answer must be citation-grounded.
    """

    system_prompt: str
    user_prompt: str
    source_map: dict[int, RetrievalCandidate]
    intent: Intent = Intent.KNOWLEDGE


REFUSAL_MESSAGE = (
    "I don't have enough verified context to answer that from the available Entrance Gateway knowledge sources."
)

# Deterministic replies used when the LLM is unavailable or produces an
# unusable conversational answer. A greeting must never fall back to the
# knowledge refusal message.
FALLBACK_GREETING = (
    "Hello! I'm the Entrance Gateway AI. I can help you explore courses, colleges, "
    "syllabuses, trainings, and entrance exam materials. What would you like to know?"
)

FALLBACK_SMALL_TALK = (
    "I'm the Entrance Gateway AI, here to help students in Nepal find courses, colleges, "
    "syllabuses, trainings, and past entrance exam questions. What can I look up for you?"
)


CONVERSATIONAL_SYSTEM_PROMPT = """You are the Entrance Gateway AI, a friendly academic assistant for students in Nepal.

The user has sent a greeting or a short conversational message. There is no knowledge retrieval for this turn.

Rules:
1. Reply warmly and naturally in 1-2 short sentences.
2. Briefly mention that you can help with courses, colleges, syllabuses, trainings, and entrance exam materials.
3. NEVER state specific facts about any course, college, fee, date, syllabus, or exam in this reply. You have no sources for this turn. If the user wants such details, invite them to ask.
4. NEVER include citation markers such as [1]. There are no sources to cite.
5. Do not apologize and do not say you lack context. This is a greeting, not a knowledge question.
6. Use plain text or simple Markdown. Do not use headings."""


def build_conversational_prompt(
    query: str,
    *,
    intent: Intent,
    recent_history: str = "",
) -> PromptBundle:
    """Build a sourceless prompt for greetings and small talk.

    Conversational turns bypass retrieval entirely, so the bundle carries an
    empty source map and the originating intent. Guardrails read that intent
    and skip the citation requirements that only apply to grounded answers.
    """

    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("query must not be empty")
    if not intent.is_conversational:
        raise ValueError("build_conversational_prompt requires a conversational intent")

    history_block = f"Recent history:\n{recent_history.strip()}\n\n" if recent_history.strip() else ""
    user_prompt = f"""{history_block}<message>
{cleaned_query}
</message>

Reply to the <message> naturally following your rules. Do not include citations and do not state specific academic facts."""

    logger.info("conversational_prompt_built", intent=intent.value, query_length=len(cleaned_query))
    return PromptBundle(
        system_prompt=CONVERSATIONAL_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        source_map={},
        intent=intent,
    )


def fallback_answer(intent: Intent) -> str:
    """Deterministic conversational reply used when generation is unusable."""

    return FALLBACK_GREETING if intent == Intent.GREETING else FALLBACK_SMALL_TALK


SYSTEM_PROMPT = """You are the Entrance Gateway AI, an expert academic assistant for students in Nepal.
Your primary task is to answer the user's question using ONLY the provided numbered sources.

Strict Rules:
1. GREETINGS & CHIT-CHAT: You may respond naturally and politely to basic conversational greetings (e.g., "hi", "hello", "how are you"). Introduce yourself if appropriate.
2. NO OUTSIDE KNOWLEDGE: For any factual question or request for information, if the sources do not contain the answer, you must reply EXACTLY: "{refusal}"
3. CITATIONS: You must cite the source for every factual claim. Place the citation at the end of the relevant sentence (e.g., [1] or [1][2]).
4. TONE & FORMAT: Be extremely concise, maximum 2-3 sentences. Use bullet points if listing items.
5. HALLUCINATION PREVENTION: Never invent citations. Only use the numbers provided in the context.
6. STRICT RELEVANCE GATE: If the provided sources are not strictly relevant to the user's specific request, ignore them and state you do not have the information.
7. RELEVANCE FILTERING: Retrieved sources are candidates, not automatic answers. Include only sources that directly match the user's requested category, topic, or constraint.
8. FALSE PREMISES: If the user assumes something unsupported, correct it using the sources. For example, do not call a business course computer-related unless the source says it is computer-related.""".format(refusal=REFUSAL_MESSAGE)


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
- If the <question> is a casual greeting, respond politely without needing sources.
- For all other questions, analyze the <context> to answer the <question>.
- Do not forget to include your inline citations (e.g., [1]).
- Either answer with citations OR refuse with the exact refusal phrase; never do both in the same response (unless continuing after a greeting).
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