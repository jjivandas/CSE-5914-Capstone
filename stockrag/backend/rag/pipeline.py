"""RAG pipeline — wire retrieval and generation together."""

from __future__ import annotations

from typing import Generator, List

from config import DEFAULT_TOP_K, RETRIEVAL_TOP_K
from rag.retrieval import format_context, retrieve
from rag.llm_service import (
    expand_query,
    get_response,
    rerank_candidates,
    stream_response,
)
from rag.vector_db import SearchResult, get_profile_by_cik


def _fetch_and_rerank(query: str, top_k: int) -> List[SearchResult]:
    """
    Two-stage retrieval:
      1. Expand the query and fetch RETRIEVAL_TOP_K candidates from ChromaDB.
      2. Use the LLM to rerank and select the top_k most relevant companies.
    Returns the filtered + reranked SearchResult list.
    """
    # Stage 1: query expansion + broad retrieval
    expanded = expand_query(query)
    candidates = retrieve(expanded, top_k=RETRIEVAL_TOP_K)

    if not candidates:
        return []

    # Stage 2: LLM reranking — select best company CIKs
    ranked_ciks = rerank_candidates(query, candidates, top_n=top_k)

    if not ranked_ciks:
        # Fallback: return top_k unique companies by vector distance
        seen: set[str] = set()
        fallback: list[SearchResult] = []
        for r in candidates:
            if r.cik not in seen:
                seen.add(r.cik)
                if len(seen) >= top_k:
                    break
            fallback.append(r)
        return fallback

    # Rebuild doc list in ranked order, preserving all docs for each company
    cik_rank = {cik: i for i, cik in enumerate(ranked_ciks)}
    filtered = [r for r in candidates if r.cik in cik_rank]
    filtered.sort(key=lambda r: cik_rank[r.cik])
    return filtered


def run(query: str, top_k: int = DEFAULT_TOP_K) -> tuple[str, List[SearchResult]]:
    """Non-streaming pipeline. Returns (response_text, retrieved_docs)."""
    docs = _fetch_and_rerank(query, top_k)
    context = format_context(docs)
    answer = get_response(query, context)
    return answer, docs


def stream(query: str, top_k: int = DEFAULT_TOP_K) -> Generator[str, None, None]:
    """Streaming pipeline. Yields text tokens from the LLM."""
    docs = _fetch_and_rerank(query, top_k)
    context = format_context(docs)
    yield from stream_response(query, context)


_SKIP_KEYS = {"cik", "entity_name", "ticker", "exchange", "doc_type", "doc_id", "fy", "concept"}


def get_sources(docs: List[SearchResult]) -> List[dict]:
    """Convert retrieved docs to source citations with financial data."""
    seen: dict[str, dict] = {}
    for d in docs:
        if d.cik not in seen:
            seen[d.cik] = {
                "cik": d.cik,
                "entity_name": d.entity_name,
                "ticker": d.ticker,
                "exchange": d.exchange,
                "doc_types": [],
                "financials": {},
                "text_snippet": "",
            }
        if d.doc_type not in seen[d.cik]["doc_types"]:
            seen[d.cik]["doc_types"].append(d.doc_type)

        # Collect ALL financial metadata — prefer profile, then snapshot, then any
        _PRIORITY = {"company_profile": 0, "annual_snapshot": 1}
        cur_priority = _PRIORITY.get(
            seen[d.cik].get("_fin_source", ""), 2
        )
        doc_priority = _PRIORITY.get(d.doc_type, 2)
        if doc_priority <= cur_priority or not seen[d.cik]["financials"]:
            fin = {k: v for k, v in d.metadata.items()
                   if k not in _SKIP_KEYS and v is not None}
            if fin:
                seen[d.cik]["financials"] = fin
                seen[d.cik]["_fin_source"] = d.doc_type

        # Capture profile text for whyFits extraction
        if d.doc_type == "company_profile" and not seen[d.cik]["text_snippet"]:
            seen[d.cik]["text_snippet"] = d.text[:500]

    # Backfill financials from profile collection for companies missing data
    for entry in seen.values():
        if not entry["financials"]:
            profile = get_profile_by_cik(entry["cik"])
            if profile:
                fin = {k: v for k, v in profile.metadata.items()
                       if k not in _SKIP_KEYS and v is not None}
                if fin:
                    entry["financials"] = fin
                if not entry["text_snippet"]:
                    entry["text_snippet"] = profile.text[:500]

    return list(seen.values())
