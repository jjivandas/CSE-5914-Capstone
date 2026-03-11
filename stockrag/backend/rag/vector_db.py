"""ChromaDB service — persistent client, collection management, and search."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import chromadb

from config import (
    CHROMA_DIR,
    DEFAULT_TOP_K,
    DESCRIPTIONS_COLLECTION,
    EMBEDDING_MODEL,
    PROFILES_COLLECTION,
    SNAPSHOTS_COLLECTION,
)
from rag.embeddings import STEmbeddingFunction


@dataclass
class SearchResult:
    doc_id: str
    text: str
    doc_type: str
    cik: str
    entity_name: str
    ticker: str
    exchange: str
    distance: float
    metadata: dict = field(default_factory=dict)


def _build_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _ef() -> STEmbeddingFunction:
    return STEmbeddingFunction(EMBEDDING_MODEL)


# ── module-level singletons (lazy) ────────────────────────────────────────────
_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def get_collection(name: str) -> chromadb.Collection:
    return get_client().get_collection(name=name, embedding_function=_ef())


def collection_exists(name: str) -> bool:
    try:
        get_client().get_collection(name)
        return True
    except Exception:
        return False


def collection_count(name: str) -> int:
    try:
        return get_collection(name).count()
    except Exception:
        return 0


# ── search ─────────────────────────────────────────────────────────────────────
def _query_collection(name: str, query: str, n_results: int) -> List[SearchResult]:
    if not collection_exists(name):
        return []
    col = get_collection(name)
    if col.count() == 0:
        return []

    results = col.query(
        query_texts=[query],
        n_results=min(n_results, col.count()),
        include=["documents", "metadatas", "distances"],
    )

    out: List[SearchResult] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        out.append(
            SearchResult(
                doc_id=meta.get("doc_id", ""),
                text=doc,
                doc_type=meta.get("doc_type", ""),
                cik=meta.get("cik", ""),
                entity_name=meta.get("entity_name", ""),
                ticker=meta.get("ticker", ""),
                exchange=meta.get("exchange", ""),
                distance=float(dist),
                metadata=meta,
            )
        )
    return out


def search(query: str, top_k: int = DEFAULT_TOP_K) -> List[SearchResult]:
    """Query all collections and merge results, deduplicating by CIK."""
    profile_results = _query_collection(PROFILES_COLLECTION, query, top_k)
    desc_results = _query_collection(DESCRIPTIONS_COLLECTION, query, top_k)
    snapshot_results = _query_collection(SNAPSHOTS_COLLECTION, query, top_k)

    # Merge profiles + description results: best (lowest distance) per CIK
    seen_profiles: dict[str, SearchResult] = {}
    for r in profile_results + desc_results:
        if r.cik not in seen_profiles or r.distance < seen_profiles[r.cik].distance:
            seen_profiles[r.cik] = r

    # Collect snapshots by CIK
    snapshot_by_cik: dict[str, list[SearchResult]] = {}
    for r in snapshot_results:
        snapshot_by_cik.setdefault(r.cik, []).append(r)

    # Also gather description docs indexed separately (to attach after profile)
    desc_by_cik: dict[str, SearchResult] = {}
    for r in desc_results:
        if r.cik not in desc_by_cik or r.distance < desc_by_cik[r.cik].distance:
            desc_by_cik[r.cik] = r

    merged: List[SearchResult] = []
    for r in sorted(seen_profiles.values(), key=lambda x: x.distance):
        merged.append(r)
        # Attach description doc if it's a different doc from the profile
        desc_doc = desc_by_cik.get(r.cik)
        if desc_doc and desc_doc.doc_id != r.doc_id:
            merged.append(desc_doc)
        # Attach up to 2 annual snapshots
        for snap in snapshot_by_cik.get(r.cik, [])[:2]:
            merged.append(snap)

    # Snapshots for CIKs not in profiles
    profile_ciks = set(seen_profiles.keys())
    for cik, snaps in snapshot_by_cik.items():
        if cik not in profile_ciks:
            merged.extend(snaps[:1])

    return merged[:top_k * 3]
