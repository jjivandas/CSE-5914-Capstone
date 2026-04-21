#!/usr/bin/env python3
"""
index_into_chroma.py — Load per-company RAG JSON files into ChromaDB.

Indexes two document types by default:
  • company_profile  (1 per company)  → collection: company_profiles
  • annual_snapshot  (≤5 per company) → collection: annual_snapshots

Optional:
  • --include-facts  — also index fact_sentence documents (large, slow)

Usage:
    python3 index_into_chroma.py
    python3 index_into_chroma.py --force          # re-index everything
    python3 index_into_chroma.py --include-facts  # add fact sentences
    python3 index_into_chroma.py --limit 100      # only process first N companies

Output:
    stockrag/chroma_db/  (ChromaDB persistent storage)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# ── paths ─────────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent
STOCKRAG_DIR = HERE.parent
RAG_DIR = HERE / "rag"
COMPANIES_DIR = RAG_DIR / "companies"
COMPANIES_INDEX = RAG_DIR / "companies_index.json"
CHROMA_DIR = STOCKRAG_DIR / "chroma_db"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
PROFILES_COLLECTION = "company_profiles"
SNAPSHOTS_COLLECTION = "annual_snapshots"
DESCRIPTIONS_COLLECTION = "company_descriptions"
FACTS_COLLECTION = "fact_sentences"

# How many documents to upsert per ChromaDB call
BATCH_SIZE = 256


# ── embedding function ────────────────────────────────────────────────────────
class _STEmbeddingFn(chromadb.EmbeddingFunction):
    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name)

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        return self._model.encode(
            list(input), normalize_embeddings=True, show_progress_bar=False
        ).tolist()


# ── helpers ───────────────────────────────────────────────────────────────────
def _get_or_create(client: chromadb.PersistentClient, name: str, ef: _STEmbeddingFn):
    return client.get_or_create_collection(name=name, embedding_function=ef)


def _already_indexed(collection, cik: str) -> bool:
    """Return True if this CIK already has at least one document in the collection."""
    result = collection.get(where={"cik": cik}, limit=1, include=[])
    return len(result["ids"]) > 0


def _upsert_batch(collection, ids, docs, metas) -> None:
    if not ids:
        return
    collection.upsert(ids=ids, documents=docs, metadatas=metas)


# ── main ──────────────────────────────────────────────────────────────────────
def run(args: argparse.Namespace) -> None:
    if not COMPANIES_INDEX.exists():
        print(f"ERROR: companies_index.json not found at {COMPANIES_INDEX}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading companies index …")
    with open(COMPANIES_INDEX) as f:
        index = json.load(f)

    companies = index["companies"]
    if args.cik:
        cik_filter = {str(cik).zfill(10) for cik in args.cik}
        companies = [
            company for company in companies
            if str(company.get("cik", "")).zfill(10) in cik_filter
        ]
    if args.limit:
        companies = companies[: args.limit]

    total = len(companies)
    print(f"Companies to process: {total}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"ChromaDB path:   {CHROMA_DIR}")
    print(f"Include facts:   {args.include_facts}")
    print()

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading embedding model …")
    ef = _STEmbeddingFn(EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    profiles_col = _get_or_create(client, PROFILES_COLLECTION, ef)
    snapshots_col = _get_or_create(client, SNAPSHOTS_COLLECTION, ef)
    descriptions_col = _get_or_create(client, DESCRIPTIONS_COLLECTION, ef)
    facts_col = _get_or_create(client, FACTS_COLLECTION, ef) if args.include_facts else None

    # Pending upsert buffers keyed by collection
    buffers: dict[str, tuple[list, list, list]] = {
        PROFILES_COLLECTION: ([], [], []),
        SNAPSHOTS_COLLECTION: ([], [], []),
        DESCRIPTIONS_COLLECTION: ([], [], []),
    }
    if args.include_facts:
        buffers[FACTS_COLLECTION] = ([], [], [])

    col_map = {
        PROFILES_COLLECTION: profiles_col,
        SNAPSHOTS_COLLECTION: snapshots_col,
        DESCRIPTIONS_COLLECTION: descriptions_col,
    }
    if args.include_facts:
        col_map[FACTS_COLLECTION] = facts_col  # type: ignore[index]

    def flush(col_name: str) -> None:
        ids, docs, metas = buffers[col_name]
        if ids:
            _upsert_batch(col_map[col_name], ids, docs, metas)
            buffers[col_name] = ([], [], [])

    def flush_all() -> None:
        for name in buffers:
            flush(name)

    ok = skipped = errors = 0
    t0 = time.perf_counter()

    for idx, entry in enumerate(companies, 1):
        cik = entry.get("cik", "")
        entity_name = entry.get("entity_name", "")
        file_path = COMPANIES_DIR / f"{cik}.json"

        if not file_path.exists():
            errors += 1
            continue

        # Resumable: skip if already indexed (unless --force)
        if not args.force and _already_indexed(profiles_col, cik):
            skipped += 1
            if idx % 500 == 0:
                elapsed = time.perf_counter() - t0
                print(
                    f"  [{idx:>5}/{total}] skipped={skipped} ok={ok} errors={errors}"
                    f"  ({elapsed:.0f}s elapsed)"
                )
            continue

        try:
            with open(file_path) as f:
                company = json.load(f)
        except Exception as exc:
            print(f"  ERROR reading {file_path.name}: {exc}")
            errors += 1
            continue

        ticker = company.get("ticker", "")
        exchange = company.get("exchange", "")

        for doc in company.get("documents", []):
            doc_type = doc.get("doc_type", "")
            text = doc.get("text", "").strip()
            meta_raw = doc.get("metadata", {})

            if not text:
                continue

            # Choose target collection
            if doc_type == "company_profile":
                col_name = PROFILES_COLLECTION
            elif doc_type == "annual_snapshot":
                col_name = SNAPSHOTS_COLLECTION
            elif doc_type == "company_description":
                col_name = DESCRIPTIONS_COLLECTION
            elif doc_type == "fact_sentence" and args.include_facts:
                col_name = FACTS_COLLECTION
            else:
                continue

            # Build a stable doc_id
            # annual_snapshot uses "fiscal_year"; fact_sentence uses "fy"
            fiscal_year = meta_raw.get("fiscal_year") or meta_raw.get("fy", "")
            concept = meta_raw.get("concept", "")
            unit = meta_raw.get("unit", "")
            end_date = meta_raw.get("end_date", "")

            if doc_type == "company_profile":
                doc_id = f"profile_{cik}"
            elif doc_type == "annual_snapshot":
                doc_id = f"snapshot_{cik}_{fiscal_year}"
            elif doc_type == "company_description":
                doc_id = f"description_{cik}"
            else:
                doc_id = f"fact_{cik}_{concept}_{unit}_{end_date}"

            # Flatten metadata for ChromaDB (only non-None scalar values)
            meta: dict[str, str | int | float | bool] = {
                "cik": cik,
                "entity_name": entity_name,
                "ticker": ticker,
                "exchange": exchange,
                "doc_type": doc_type,
                "doc_id": doc_id,
            }
            if fiscal_year is not None and fiscal_year != "":
                fy_val = fiscal_year
                meta["fy"] = int(fy_val) if str(fy_val).isdigit() else str(fy_val)
            if concept:
                meta["concept"] = concept

            # Propagate ALL numeric/string financial metadata into ChromaDB.
            # Skip keys already set above and internal-only keys.
            _SKIP_KEYS = {"cik", "entity_name", "ticker", "exchange", "doc_type",
                          "doc_id", "fy", "concept", "description_source",
                          "taxonomy", "accession_number", "form", "filed_date",
                          "period_key", "fp", "start_date", "end_date",
                          "period_type", "last_filing_date"}
            for fk, val in meta_raw.items():
                if fk in _SKIP_KEYS or fk in meta:
                    continue
                if val is None or val == "":
                    continue
                # ChromaDB metadata supports str, int, float, bool only
                if isinstance(val, (int, float, bool)):
                    meta[fk] = val
                elif isinstance(val, str):
                    meta[fk] = val

            ids, docs_buf, metas_buf = buffers[col_name]
            ids.append(doc_id)
            docs_buf.append(text)
            metas_buf.append(meta)

            # Flush when batch is full
            if len(ids) >= BATCH_SIZE:
                flush(col_name)

        ok += 1

        # Periodic progress
        if idx % 100 == 0 or idx == total:
            elapsed = time.perf_counter() - t0
            rate = ok / max(elapsed, 1)
            eta = (total - idx) / max(rate, 0.001)
            print(
                f"  [{idx:>5}/{total}] ok={ok:>5} skip={skipped:>5} err={errors:>3}"
                f"  {rate:.1f} co/s  ETA {eta:.0f}s"
            )

    # Final flush
    flush_all()

    elapsed = time.perf_counter() - t0
    print()
    print("=" * 60)
    print(f"Done in {elapsed:.1f}s")
    print(f"  Companies processed : {ok}")
    print(f"  Skipped (cached)    : {skipped}")
    print(f"  Errors              : {errors}")
    print(f"  Profiles indexed     : {profiles_col.count()}")
    print(f"  Descriptions indexed : {descriptions_col.count()}")
    print(f"  Snapshots indexed    : {snapshots_col.count()}")
    if facts_col:
        print(f"  Facts indexed        : {facts_col.count()}")


# ── CLI ───────────────────────────────────────────────────────────────────────
def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Index company RAG documents into ChromaDB")
    p.add_argument("--force", action="store_true", help="Re-index even if already indexed")
    p.add_argument("--include-facts", action="store_true", help="Also index fact_sentence documents (slow)")
    p.add_argument("--limit", type=int, default=0, help="Only process first N companies (0 = all)")
    p.add_argument("--cik", action="append", default=[],
                   help="Only process the specified CIK. Repeat for multiple companies.")
    return p.parse_args()


if __name__ == "__main__":
    run(_parse())
