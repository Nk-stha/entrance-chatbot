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


# Every static instruction lives here rather than in the user prompt.
#
# Two measured reasons:
#  * Refusal bias. The previous prompt gave eight separate directives to refuse
#    or discard sources, which drove a 3B model to emit the refusal phrase even
#    when it had been handed the correct, relevant source. There is now exactly
#    one refusal rule, stated as the exception rather than the default.
#  * Prefill cost. Ollama caches the prompt prefix. Static text placed after the
#    variable <context> block cannot be cached and was re-processed at ~30ms per
#    token on every request. Keeping it in the constant system prefix removes it
#    from per-request prefill entirely.
SYSTEM_PROMPT = """You are the Entrance Gateway AI, an academic assistant for students in Nepal.

Answer the user's question using the numbered sources given in <context>.

1. GROUND YOUR ANSWER: If the sources address the question, even partially, answer from them. Prefer giving the user what the sources do support over declining.
2. WRITE, DO NOT COPY: Answer in your own words as a direct reply to the user. Never repeat the source block itself - do not output "Title:", "Content:", or a leading "[n] Title: ..." line.
3. CITATIONS: Cite every factual claim with its source number, for example [1] or [1][2]. Only use numbers that appear in <context>, and never invent one.
4. STAY ON TARGET: Answer what was actually asked. Do not present a source as matching a category it does not match - for example, do not describe a business course as computer-related.
5. TONE AND FORMAT: Be concise. Two or three sentences, or a short bullet list. Use Markdown.
6. WHEN YOU CANNOT ANSWER: Only if none of the sources address the question, reply with exactly this sentence and nothing else:
"{refusal}"
Never combine that sentence with an answer or a citation.""".format(refusal=REFUSAL_MESSAGE)


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
    # History is fenced in its own tag so the model cannot mistake a previous
    # answer for retrieved evidence. Without the fence a 3B model copies the
    # prior answer instead of reading <context> - the "asked about CSIT, got the
    # BCA answer again" failure.
    history_block = (
        f"<history>\n{recent_history.strip()}\n</history>\n\n" if recent_history.strip() else ""
    )
    # Variable content only. Anything static belongs in SYSTEM_PROMPT so that it
    # stays inside Ollama's cached prefix.
    # One short reminder stays here, immediately before the generation point.
    # Measured: with the citation rule only in the distant system prompt, the 3B
    # model answered without citations on 5/5 runs and every answer was then
    # rejected by the citation guardrail. Proximity matters more than the ~15
    # tokens of prefill this costs.
    user_prompt = f"""{history_block}<context>
{context if context else 'No sources available.'}
</context>

<question>
{cleaned_query}
</question>

Answer the <question> using only the numbered sources in <context>, in your own words. Earlier turns in <history> are background for understanding follow-ups - never copy facts from them. End each factual sentence with its source number, like [1]."""

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