"""
Parse SEC EDGAR company facts JSON files into normalized parquet tables.

Reads from: stockrag/companyfacts/CIK*.json  (raw XBRL facts)
Writes to:  stockrag/data/processed/sec/
  - entity_master.parquet : one row per company (CIK anchor)
  - concepts.parquet      : dimension table (taxonomy, concept → label, description)
  - facts.parquet         : event table with dedup ranking and period semantics
  - filings.parquet       : one row per unique filing
Writes to:  stockrag/data/rag/
  - sec_facts_index.parquet : Tier-1 preferred fact sentences for embedding

Architecture reference: update_data_readme.md
Data format reference:  docs/company_facts_report.md

Design principles:
  - Fail loud: schema violations raise immediately, never silently produce wrong data.
  - Skip empty: files < 100 bytes are logged and skipped (known SEC EDGAR issue).
  - Normalized: no repeated label/description text in facts; join via concepts table.
  - Ranked: every fact gets revision_rank + is_preferred for dedup (Section 7).
  - RAG-ready: Tier-1 preferred facts are turned into natural language sentences.
  - Memory-efficient: facts written incrementally via PyArrow ParquetWriter.
  - Resumable: already-processed runs are skipped unless --force is passed.
"""

import argparse
import json
import logging
import sys
import time
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_FILE_SIZE_BYTES = 100

REQUIRED_TOP_KEYS = {"cik", "entityName", "facts"}
REQUIRED_DATAPOINT_FIELDS = {"end", "val", "accn", "fy", "fp", "form", "filed"}

# Form priority for dedup ranking (lower = preferred)
FORM_PRIORITY = {
    "10-K": 0,
    "10-K/A": 1,
    "20-F": 2,
    "20-F/A": 3,
    "10-Q": 4,
    "10-Q/A": 5,
    "8-K": 6,
    "8-K/A": 7,
}
DEFAULT_FORM_PRIORITY = 99

# Tier-1 concepts: core financials always indexed for RAG (Section 8.1)
TIER1_CONCEPTS = {
    # DEI
    "EntityCommonStockSharesOutstanding",
    "EntityPublicFloat",
    # Balance Sheet
    "Assets",
    "AssetsCurrent",
    "Liabilities",
    "LiabilitiesCurrent",
    "LiabilitiesAndStockholdersEquity",
    "StockholdersEquity",
    "RetainedEarningsAccumulatedDeficit",
    "CashAndCashEquivalentsAtCarryingValue",
    "PropertyPlantAndEquipmentNet",
    # Income Statement
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "CostOfRevenue",
    "CostOfGoodsAndServicesSold",
    "GrossProfit",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    "IncomeTaxExpenseBenefit",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    # Cash Flow
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInInvestingActivities",
    "NetCashProvidedByUsedInFinancingActivities",
    # Shares
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "WeightedAverageNumberOfSharesOutstandingDiluted",
    "CommonStockSharesOutstanding",
}

# ---------------------------------------------------------------------------
# PyArrow schemas
# ---------------------------------------------------------------------------

ENTITY_SCHEMA = pa.schema([
    ("cik", pa.string()),
    ("entity_name", pa.string()),
    ("last_seen_filing_date", pa.string()),
    ("snapshot_date", pa.string()),
    ("partial", pa.bool_()),
])

CONCEPT_SCHEMA = pa.schema([
    ("taxonomy", pa.string()),
    ("concept", pa.string()),
    ("label", pa.string()),
    ("description", pa.string()),
])

FACTS_SCHEMA = pa.schema([
    ("cik", pa.string()),
    ("taxonomy", pa.string()),
    ("concept", pa.string()),
    ("unit", pa.string()),
    ("value", pa.float64()),
    ("start_date", pa.string()),
    ("end_date", pa.string()),
    ("fy", pa.int32()),
    ("fp", pa.string()),
    ("form", pa.string()),
    ("filed_date", pa.string()),
    ("accession_number", pa.string()),
    ("frame", pa.string()),
    ("period_type", pa.string()),
    ("period_key", pa.string()),
    ("revision_rank", pa.int32()),
    ("is_preferred", pa.bool_()),
])

FILINGS_SCHEMA = pa.schema([
    ("cik", pa.string()),
    ("accession_number", pa.string()),
    ("form", pa.string()),
    ("filed_date", pa.string()),
])

RAG_SCHEMA = pa.schema([
    ("cik", pa.string()),
    ("entity_name", pa.string()),
    ("taxonomy", pa.string()),
    ("concept", pa.string()),
    ("label", pa.string()),
    ("unit", pa.string()),
    ("value", pa.float64()),
    ("end_date", pa.string()),
    ("start_date", pa.string()),
    ("period_type", pa.string()),
    ("period_key", pa.string()),
    ("fy", pa.int32()),
    ("fp", pa.string()),
    ("form", pa.string()),
    ("filed_date", pa.string()),
    ("accession_number", pa.string()),
    ("sentence", pa.string()),
])

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Truncated JSON repair
# ---------------------------------------------------------------------------


def repair_truncated_json(raw: str, filepath: str) -> dict | None:
    """
    Recover a truncated JSON file by finding the last valid closing bracket
    and sealing all remaining open structures.

    Returns the parsed dict on success, None if unrecoverable.
    """
    stack: list[str] = []
    last_good_pos = 0
    stack_at_good: list[str] = []
    in_string = False
    escape_next = False

    for i, ch in enumerate(raw):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if ch in "{[":
            stack.append(ch)
        elif ch == "}":
            if not stack or stack[-1] != "{":
                break
            stack.pop()
            last_good_pos = i + 1
            stack_at_good = list(stack)
        elif ch == "]":
            if not stack or stack[-1] != "[":
                break
            stack.pop()
            last_good_pos = i + 1
            stack_at_good = list(stack)

    if last_good_pos == 0:
        return None

    repaired = raw[:last_good_pos]
    for bracket in reversed(stack_at_good):
        repaired += "]" if bracket == "[" else "}"

    try:
        data = json.loads(repaired)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None
    if not REQUIRED_TOP_KEYS.issubset(data.keys()):
        return None

    log.info(
        "REPAIRED %s: recovered %d / %d bytes (%.1f%%)",
        filepath, last_good_pos, len(raw), last_good_pos / len(raw) * 100,
    )
    return data


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_top_level(data: dict, filepath: str) -> None:
    """Assert the JSON has the expected top-level keys."""
    missing = REQUIRED_TOP_KEYS - data.keys()
    if missing:
        raise ValueError(f"{filepath}: missing required top-level keys: {missing}")

    if isinstance(data["cik"], str):
        if not data["cik"].strip().isdigit():
            raise ValueError(f"{filepath}: 'cik' is a non-numeric string: {data['cik']!r}")
        data["cik"] = int(data["cik"].strip())
    if not isinstance(data["cik"], int):
        raise TypeError(f"{filepath}: 'cik' must be int, got {type(data['cik']).__name__}")
    if not isinstance(data["entityName"], str) or not data["entityName"].strip():
        raise ValueError(f"{filepath}: 'entityName' is empty or not a string")
    if not isinstance(data["facts"], dict):
        raise TypeError(f"{filepath}: 'facts' must be dict, got {type(data['facts']).__name__}")


def validate_datapoint(dp: dict, context: str) -> None:
    """Assert a single datapoint has all required fields."""
    missing = REQUIRED_DATAPOINT_FIELDS - dp.keys()
    if missing:
        raise ValueError(f"{context}: datapoint missing fields: {missing}")


# ---------------------------------------------------------------------------
# Derived fields (Section 5.4, 6, 7)
# ---------------------------------------------------------------------------


def compute_period_type(start_date: str) -> str:
    """instant if no start_date, duration if present."""
    return "duration" if start_date else "instant"


def compute_period_key(fy: int | None, fp: str | None,
                       start_date: str, end_date: str) -> str:
    """Stable period key: prefer fy-fp, fall back to date range."""
    if fy and fp:
        return f"{fy}-{fp}"
    if start_date:
        return f"{start_date}:{end_date}"
    return end_date


def dedup_rank_facts(facts: list[dict]) -> list[dict]:
    """
    Rank duplicate datapoints within a single company's facts.

    Groups by (taxonomy, concept, unit, start_date, end_date, fy, fp).
    Ranks by: latest filed_date first, then form priority (10-K > 10-Q).
    Assigns revision_rank (1=best) and is_preferred (rank==1).
    """
    # Build group key → list of indices
    groups: dict[tuple, list[int]] = {}
    for idx, f in enumerate(facts):
        key = (
            f["taxonomy"], f["concept"], f["unit"],
            f["start_date"], f["end_date"], f["fy"], f["fp"],
        )
        groups.setdefault(key, []).append(idx)

    for indices in groups.values():
        # Sort: latest filed_date first, then lower form priority number
        indices.sort(key=lambda i: (
            facts[i]["filed_date"],                                          # DESC (later is better)
            -FORM_PRIORITY.get(facts[i]["form"], DEFAULT_FORM_PRIORITY),     # lower priority number = better
        ), reverse=True)

        for rank, i in enumerate(indices, 1):
            facts[i]["revision_rank"] = rank
            facts[i]["is_preferred"] = (rank == 1)

    return facts


# ---------------------------------------------------------------------------
# Core parsing
# ---------------------------------------------------------------------------


def extract_from_file(data: dict, filepath: str, partial: bool = False) -> tuple[
    list[dict],   # facts rows
    dict[tuple[str, str], tuple[str, str]],  # concepts: (taxonomy, concept) → (label, desc)
    set[tuple[str, str, str, str]],          # filings: (cik, accn, form, filed)
]:
    """
    Extract facts, concepts, and filings from a parsed company facts dict.

    Returns (facts_rows, concepts_dict, filings_set).
    """
    cik_str = str(data["cik"]).zfill(10)
    facts_rows: list[dict] = []
    concepts: dict[tuple[str, str], tuple[str, str]] = {}
    filings: set[tuple[str, str, str, str]] = set()

    for taxonomy, taxonomy_concepts in data["facts"].items():
        if not isinstance(taxonomy_concepts, dict):
            if partial:
                continue
            raise TypeError(
                f"{filepath}: taxonomy '{taxonomy}' value must be dict, "
                f"got {type(taxonomy_concepts).__name__}"
            )

        for concept_name, concept_body in taxonomy_concepts.items():
            if not isinstance(concept_body, dict):
                if partial:
                    continue
                raise TypeError(f"{filepath}: concept '{taxonomy}.{concept_name}' must be dict")

            label = concept_body.get("label", "")
            description = concept_body.get("description", "")
            units = concept_body.get("units")

            # Register concept in dimension table
            concepts[(taxonomy, concept_name)] = (label, description)

            if units is None:
                if partial:
                    continue
                raise ValueError(f"{filepath}: concept '{taxonomy}.{concept_name}' has no 'units' key")
            if not isinstance(units, dict):
                if partial:
                    continue
                raise TypeError(f"{filepath}: concept '{taxonomy}.{concept_name}' units must be dict")

            for unit_name, datapoints in units.items():
                if not isinstance(datapoints, list):
                    if partial:
                        continue
                    raise TypeError(
                        f"{filepath}: '{taxonomy}.{concept_name}.{unit_name}' "
                        f"must be list, got {type(datapoints).__name__}"
                    )

                for i, dp in enumerate(datapoints):
                    ctx = f"{filepath}: {taxonomy}.{concept_name}.{unit_name}[{i}]"

                    if partial and not REQUIRED_DATAPOINT_FIELDS.issubset(dp.keys()):
                        continue

                    validate_datapoint(dp, ctx)

                    start_date = dp.get("start", "")
                    end_date = dp["end"]
                    fy = dp["fy"]
                    fp = dp["fp"]

                    # Coerce value to float for uniform storage
                    try:
                        val = float(dp["val"])
                    except (ValueError, TypeError):
                        raise ValueError(f"{ctx}: 'val' is not numeric: {dp['val']!r}")

                    facts_rows.append({
                        "cik": cik_str,
                        "taxonomy": taxonomy,
                        "concept": concept_name,
                        "unit": unit_name,
                        "value": val,
                        "start_date": start_date,
                        "end_date": end_date,
                        "fy": fy if isinstance(fy, int) else None,
                        "fp": fp if isinstance(fp, str) else "",
                        "form": dp["form"],
                        "filed_date": dp["filed"],
                        "accession_number": dp["accn"],
                        "frame": dp.get("frame", ""),
                        "period_type": compute_period_type(start_date),
                        "period_key": compute_period_key(fy, fp, start_date, end_date),
                    })

                    # Register filing
                    filings.add((cik_str, dp["accn"], dp["form"], dp["filed"]))

    return facts_rows, concepts, filings


def build_rag_sentences(
    facts: list[dict], entity_name: str,
    concepts: dict[tuple[str, str], tuple[str, str]],
) -> list[dict]:
    """
    Build RAG fact sentences for preferred Tier-1 facts.

    Template (Section 8.2):
      {entity_name} reported {label} = {value} {unit} for period ending
      {end_date} (Form {form}, filed {filed_date}, accession {accession_number}).
    """
    rows = []
    for f in facts:
        if not f["is_preferred"]:
            continue
        if f["concept"] not in TIER1_CONCEPTS:
            continue

        label = concepts.get((f["taxonomy"], f["concept"]), ("", ""))[0]
        if not label:
            label = f["concept"]

        # Format value: integers show without decimals, others with 2dp
        val = f["value"]
        val_str = f"{val:,.0f}" if val == int(val) else f"{val:,.2f}"

        # Build period phrase
        if f["period_type"] == "duration" and f["start_date"]:
            period = f"for period {f['start_date']} to {f['end_date']}"
        else:
            period = f"as of {f['end_date']}"

        sentence = (
            f"{entity_name} reported {label} = {val_str} {f['unit']} "
            f"{period} "
            f"(Form {f['form']}, filed {f['filed_date']}, "
            f"accession {f['accession_number']})."
        )

        rows.append({
            "cik": f["cik"],
            "entity_name": entity_name,
            "taxonomy": f["taxonomy"],
            "concept": f["concept"],
            "label": label,
            "unit": f["unit"],
            "value": f["value"],
            "end_date": f["end_date"],
            "start_date": f["start_date"],
            "period_type": f["period_type"],
            "period_key": f["period_key"],
            "fy": f["fy"],
            "fp": f["fp"],
            "form": f["form"],
            "filed_date": f["filed_date"],
            "accession_number": f["accession_number"],
            "sentence": sentence,
        })

    return rows


# ---------------------------------------------------------------------------
# Arrow table helpers
# ---------------------------------------------------------------------------


def dicts_to_table(rows: list[dict], schema: pa.Schema) -> pa.Table:
    """Convert list of dicts to a PyArrow Table, coercing to schema."""
    if not rows:
        return schema.empty_table()

    columns = {}
    for field in schema:
        col_data = [r.get(field.name) for r in rows]
        columns[field.name] = col_data

    return pa.table(columns, schema=schema)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run(
    input_dir: Path,
    output_dir: Path,
    rag_dir: Path,
    force: bool = False,
    fail_fast: bool = False,
) -> None:
    """Process all company facts files into normalized parquet tables."""

    sec_dir = output_dir / "sec"
    facts_path = sec_dir / "facts.parquet"

    # Check if already processed (unless --force)
    if not force and facts_path.exists():
        log.info("Output already exists at %s — use --force to reprocess.", facts_path)
        return

    json_files = sorted(input_dir.glob("CIK*.json"))
    total = len(json_files)

    if total == 0:
        log.error("No CIK*.json files found in %s", input_dir)
        sys.exit(1)

    log.info("Found %d company files in %s", total, input_dir)
    log.info("Output: %s  |  RAG: %s", sec_dir, rag_dir)

    sec_dir.mkdir(parents=True, exist_ok=True)
    rag_dir.mkdir(parents=True, exist_ok=True)

    # Accumulators (small tables kept in memory)
    entity_rows: list[dict] = []
    all_concepts: dict[tuple[str, str], tuple[str, str]] = {}
    all_filings: set[tuple[str, str, str, str]] = set()
    rag_rows: list[dict] = []

    # Incremental writer for facts (large table, written per-company)
    facts_writer = pq.ParquetWriter(str(facts_path), FACTS_SCHEMA, compression="snappy")

    counts = {"ok": 0, "repaired": 0, "skipped_empty": 0, "error": 0}
    errors: list[tuple[str, str]] = []

    today = date.today().isoformat()
    t0 = time.monotonic()

    try:
        for i, filepath in enumerate(json_files, 1):
            if i % 500 == 0 or i == total:
                elapsed = time.monotonic() - t0
                rate = i / elapsed if elapsed > 0 else 0
                log.info(
                    "Progress: %d/%d (%.0f/s) | ok=%d repaired=%d skipped=%d errors=%d",
                    i, total, rate,
                    counts["ok"], counts["repaired"],
                    counts["skipped_empty"], counts["error"],
                )

            # Skip tiny/empty files
            file_size = filepath.stat().st_size
            if file_size < MIN_FILE_SIZE_BYTES:
                counts["skipped_empty"] += 1
                continue

            try:
                # Load JSON
                partial = False
                with open(filepath, "r", encoding="utf-8") as f:
                    raw = f.read()

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = repair_truncated_json(raw, filepath.name)
                    if data is None:
                        raise
                    partial = True

                validate_top_level(data, filepath.name)

                # Extract
                facts, concepts, filings = extract_from_file(
                    data, filepath.name, partial=partial,
                )

                # Dedup rank within this company
                if facts:
                    dedup_rank_facts(facts)

                # Entity master row
                cik_str = str(data["cik"]).zfill(10)
                last_filed = max(
                    (f["filed_date"] for f in facts if f["filed_date"]),
                    default="",
                )
                entity_rows.append({
                    "cik": cik_str,
                    "entity_name": data["entityName"],
                    "last_seen_filing_date": last_filed,
                    "snapshot_date": today,
                    "partial": partial,
                })

                # Merge concepts and filings
                all_concepts.update(concepts)
                all_filings.update(filings)

                # Write facts incrementally
                if facts:
                    facts_table = dicts_to_table(facts, FACTS_SCHEMA)
                    facts_writer.write_table(facts_table)

                # RAG sentences for this company
                rag_rows.extend(
                    build_rag_sentences(facts, data["entityName"], concepts)
                )

                counts["repaired" if partial else "ok"] += 1

            except Exception as e:
                counts["error"] += 1
                error_msg = f"{type(e).__name__}: {e}"
                errors.append((filepath.name, error_msg))
                log.error("FAILED %s: %s", filepath.name, error_msg)
                if fail_fast:
                    log.error("--fail-fast set, aborting.")
                    sys.exit(1)
    finally:
        facts_writer.close()

    elapsed = time.monotonic() - t0

    # Write entity_master
    entity_table = dicts_to_table(entity_rows, ENTITY_SCHEMA)
    pq.write_table(entity_table, str(sec_dir / "entity_master.parquet"), compression="snappy")
    log.info("Wrote entity_master.parquet: %d rows", len(entity_rows))

    # Write concepts
    concept_rows = [
        {"taxonomy": k[0], "concept": k[1], "label": v[0], "description": v[1]}
        for k, v in sorted(all_concepts.items())
    ]
    concept_table = dicts_to_table(concept_rows, CONCEPT_SCHEMA)
    pq.write_table(concept_table, str(sec_dir / "concepts.parquet"), compression="snappy")
    log.info("Wrote concepts.parquet: %d rows", len(concept_rows))

    # Write filings
    filing_rows = [
        {"cik": f[0], "accession_number": f[1], "form": f[2], "filed_date": f[3]}
        for f in sorted(all_filings)
    ]
    filing_table = dicts_to_table(filing_rows, FILINGS_SCHEMA)
    pq.write_table(filing_table, str(sec_dir / "filings.parquet"), compression="snappy")
    log.info("Wrote filings.parquet: %d rows", len(filing_rows))

    # Write RAG index
    rag_table = dicts_to_table(rag_rows, RAG_SCHEMA)
    pq.write_table(rag_table, str(rag_dir / "sec_facts_index.parquet"), compression="snappy")
    log.info("Wrote sec_facts_index.parquet: %d sentences", len(rag_rows))

    # Write manifest
    manifest = {
        "total_files": total,
        "processed_ok": counts["ok"],
        "repaired_truncated": counts["repaired"],
        "skipped_empty": counts["skipped_empty"],
        "errors": counts["error"],
        "elapsed_seconds": round(elapsed, 1),
        "entities": len(entity_rows),
        "unique_concepts": len(concept_rows),
        "unique_filings": len(filing_rows),
        "rag_sentences": len(rag_rows),
        "failed_files": [{"file": f, "error": e} for f, e in errors],
    }
    manifest_path = sec_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    log.info("=" * 60)
    log.info("DONE in %.1fs", elapsed)
    log.info("  OK: %d | Repaired: %d | Skipped: %d | Errors: %d",
             counts["ok"], counts["repaired"], counts["skipped_empty"], counts["error"])
    log.info("  Entities: %d | Concepts: %d | Filings: %d | RAG sentences: %d",
             len(entity_rows), len(concept_rows), len(filing_rows), len(rag_rows))

    if errors:
        log.warning("  %d files had errors — see manifest.json", len(errors))

    if counts["error"] > 0:
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse SEC EDGAR company facts into normalized parquet tables.",
        epilog="See update_data_readme.md for architecture details.",
    )

    script_dir = Path(__file__).resolve().parent   # stockrag/data/
    stockrag_dir = script_dir.parent               # stockrag/

    parser.add_argument(
        "--input-dir", type=Path,
        default=stockrag_dir / "companyfacts",
        help="Path to companyfacts/ directory (default: stockrag/companyfacts/)",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=script_dir,
        help="Base output directory — writes to <output-dir>/processed/sec/ (default: stockrag/data/)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-process even if output already exists",
    )
    parser.add_argument(
        "--fail-fast", action="store_true",
        help="Abort on first error instead of continuing",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.input_dir.is_dir():
        log.error("Input directory does not exist: %s", args.input_dir)
        sys.exit(1)

    run(
        input_dir=args.input_dir,
        output_dir=args.output_dir / "processed",
        rag_dir=args.output_dir / "rag",
        force=args.force,
        fail_fast=args.fail_fast,
    )


if __name__ == "__main__":
    main()
