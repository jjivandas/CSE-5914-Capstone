"""Gemini LLM client — streaming responses via the Google Gen AI SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generator, List

from google import genai
from google.genai import types

from config import GOOGLE_API_KEY, LLM_MAX_TOKENS, LLM_MODEL

if TYPE_CHECKING:
    from rag.vector_db import SearchResult

_SYSTEM_PROMPT = """You are StockRAG, an AI financial research assistant that helps users find and analyse publicly listed companies based on SEC EDGAR filings.

Your goal is to provide clear, data-driven answers about stocks and companies, using the retrieved financial context provided to you. Follow these principles:

1. **Ground every claim in the provided context.** Cite the company name, ticker, and fiscal year when referencing a number.
2. **Be balanced.** Present both strengths and risks where relevant.
3. **Be concise but complete.** Busy investors value precision.
4. **Do not invent numbers.** If the data is not in the context, say so clearly.
5. **Format your response clearly**: use bullet points, bold labels, and section headers where helpful.

When recommending or highlighting stocks, always explain *why* based on the financial data — e.g., revenue growth rate, margins, balance-sheet strength, cash generation.
"""

_DISCLAIMER = (
    "\n\n---\n*This analysis is generated from SEC EDGAR filings and is for "
    "informational purposes only. It is not financial advice. Always do your own "
    "research before making investment decisions.*"
)


def _user_prompt(
    query: str, context: str, conversation_history: list | None = None
) -> str:
    parts: list[str] = []

    if conversation_history:
        parts.append("## Conversation History")
        for msg in conversation_history[-10:]:
            label = "User" if msg.role == "user" else "Assistant"
            text = msg.content[:500] if msg.role == "assistant" else msg.content
            parts.append(f"**{label}:** {text}")
        parts.append("")

    parts.append(f"## User Query\n{query}\n")
    parts.append(f"## Retrieved Financial Context\n{context}\n")
    parts.append(
        "Please answer the user's query based on the context above. "
        "Use conversation history (if present) to resolve references like "
        "'they', 'those stocks', 'the first one', etc. "
        "If the context doesn't contain enough information to fully answer, "
        "say so and share what you do know."
    )
    return "\n".join(parts)


_cached_client: genai.Client | None = None


def _client() -> genai.Client:
    global _cached_client
    if _cached_client is None:
        _cached_client = genai.Client(api_key=GOOGLE_API_KEY)
    return _cached_client


def _config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        max_output_tokens=LLM_MAX_TOKENS,
    )


def stream_response(
    query: str, context: str, conversation_history: list | None = None
) -> Generator[str, None, None]:
    """Yield text tokens as they stream from Gemini."""
    client = _client()
    for chunk in client.models.generate_content_stream(
        model=LLM_MODEL,
        contents=_user_prompt(query, context, conversation_history),
        config=_config(),
    ):
        if chunk.text:
            yield chunk.text

    yield _DISCLAIMER


def get_response(
    query: str, context: str, conversation_history: list | None = None
) -> str:
    """Non-streaming version — returns full response text."""
    client = _client()
    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=_user_prompt(query, context, conversation_history),
        config=_config(),
    )
    return (response.text or "") + _DISCLAIMER


def expand_query(query: str, prior_context: str | None = None) -> str:
    """
    Rewrite a natural-language query into search terms likely to appear in
    SEC EDGAR filings and company descriptions.

    E.g. "GPU companies" -> "semiconductor graphics processing unit NVIDIA AMD
    computing hardware technology revenue"
    """
    context_hint = ""
    if prior_context:
        context_hint = (
            f"\nPrevious conversation context: {prior_context}\n"
            "Use this to resolve vague references in the query.\n"
        )

    prompt = (
        "Convert the following investment query into a short list of search keywords "
        "that would match SEC EDGAR company filings, industry descriptions, product "
        "categories, and financial data. Include company names, sector terms, product "
        "types, and financial metrics if relevant. "
        "Return only comma-separated keywords on a single line, no explanation.\n\n"
        f"{context_hint}"
        f"Query: {query}"
    )
    try:
        response = _client().models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=80),
        )
        expanded = (response.text or "").strip()
        return expanded if expanded else query
    except Exception:
        return query


def detect_topic_shift(
    new_query: str, conversation_history: list | None
) -> bool:
    """
    Return True if the new query is a fresh topic (no prior context should be
    carried over), False if it's a continuation of the previous turn.

    Uses a single cheap Gemini call comparing the previous USER message to the
    new query. On any failure, returns True — the safer default given the
    current over-anchoring behavior.
    """
    if not conversation_history:
        return True

    last_user_msg = None
    for msg in reversed(conversation_history):
        if msg.role == "user":
            last_user_msg = msg.content
            break
    if not last_user_msg:
        return True

    prompt = (
        "You are a topic-shift detector for a financial Q&A system.\n"
        "Decide whether the user's NEW query is a CONTINUATION of the previous "
        "query or a SHIFT to a different topic.\n\n"
        "Rules:\n"
        "- CONTINUE: follow-up questions, asking for more detail, referencing "
        "previous results with pronouns (they, those, which one, the first), "
        "asking to compare previous results with another company.\n"
        "- SHIFT: the new query names a different sector, a different universe "
        "of companies, or an unrelated question. If the sector or company set "
        "is clearly different, return SHIFT even if both are 'tech'.\n\n"
        f"Previous query: {last_user_msg}\n"
        f"New query: {new_query}\n\n"
        "Reply with exactly one word: CONTINUE or SHIFT"
    )
    try:
        response = _client().models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=4),
        )
        answer = (response.text or "").strip().upper()
        return "SHIFT" in answer
    except Exception:
        return True


def rerank_candidates(query: str, candidates: "List[SearchResult]", top_n: int) -> list[str]:
    """
    Use the LLM to select the top_n most relevant company CIKs from a
    candidate list retrieved by vector search.

    Returns an ordered list of CIK strings (most relevant first).
    Falls back to distance-ordered CIKs if the LLM call fails.
    """
    # Deduplicate by CIK, keep best (lowest distance) doc per company
    seen: dict[str, "SearchResult"] = {}
    for r in candidates:
        if r.cik not in seen or r.distance < seen[r.cik].distance:
            seen[r.cik] = r

    unique = sorted(seen.values(), key=lambda x: x.distance)
    if len(unique) <= top_n:
        return [c.cik for c in unique]

    lines = []
    for i, r in enumerate(unique, 1):
        ticker_str = f" ({r.ticker})" if r.ticker else ""
        snippet = r.text[:300].replace("\n", " ")
        lines.append(f"{i}. CIK:{r.cik} | {r.entity_name}{ticker_str}\n   {snippet}")

    company_list = "\n".join(lines)
    prompt = (
        f'User query: "{query}"\n\n'
        f"From the companies below, select the {top_n} most relevant to the query "
        f"and return their CIK numbers in order of relevance, one per line.\n"
        f"Format each line exactly as: CIK:XXXXXXXXXX\n"
        f"Return only CIK lines, nothing else.\n\n"
        f"Companies:\n{company_list}"
    )

    try:
        response = _client().models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=300),
        )
        ranked: list[str] = []
        for line in (response.text or "").strip().split("\n"):
            line = line.strip()
            if line.startswith("CIK:"):
                cik = line[4:].strip()
                if cik in seen and cik not in ranked:
                    ranked.append(cik)
        if ranked:
            return ranked[:top_n]
    except Exception:
        pass

    # Fallback: distance order
    return [c.cik for c in unique[:top_n]]
