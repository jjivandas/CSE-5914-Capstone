"""Retrieval layer — fetch documents from ChromaDB and format as LLM context."""

from __future__ import annotations

from typing import List

from rag.vector_db import SearchResult, search


def retrieve(query: str, top_k: int = 5) -> List[SearchResult]:
    """Return relevant documents for a query."""
    return search(query, top_k=top_k)


def format_context(results: List[SearchResult]) -> str:
    """Convert retrieved documents into a structured context block for the LLM."""
    if not results:
        return "No relevant company data found in the database."

    sections: List[str] = []
    seen_ciks: set[str] = set()

    for r in results:
        header = f"### {r.entity_name}"
        if r.ticker:
            header += f" ({r.ticker})"
        if r.exchange:
            header += f" — {r.exchange}"
        header += f" | CIK {r.cik}"

        # Add source label so the LLM knows what type of doc this is
        if r.doc_type == "annual_snapshot":
            fy = r.metadata.get("fiscal_year") or r.metadata.get("fy", "")
            header += f"\n*Source: Annual Snapshot FY{fy}*"
        elif r.doc_type == "company_profile":
            header += "\n*Source: Company Profile*"
        else:
            header += f"\n*Source: {r.doc_type}*"

        sections.append(f"{header}\n\n{r.text}")
        seen_ciks.add(r.cik)

    companies_found = len(seen_ciks)
    header_line = f"*{companies_found} compan{'y' if companies_found == 1 else 'ies'} found — {len(results)} document(s) retrieved*\n\n"
    return header_line + "\n\n---\n\n".join(sections)
