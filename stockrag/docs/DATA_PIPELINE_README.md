# Data Pipeline: Company Facts Parser

## What Changed (and Why)

The parsing script (`parse_company_facts.py`) was rewritten to follow the architecture in `update_data_readme.md`. Here's what's different and why it matters.

---

### Before: Per-company CSV folders

```
data/processed/
  CIK0000320193/
    metadata.json       # company info
    financials.csv      # ALL datapoints in one flat CSV
    summary.json        # stats
  CIK0000001750/
    ...
  (7,138 folders, ~27 GB total)
```

**Problems:**
- `label` and `description` text repeated on every single row (massive redundancy)
- `entity_name` repeated on every row
- No deduplication: same metric appears in both 10-K and 10-Q for same period
- No way to query across companies without reading thousands of files
- No distinction between instant (balance sheet) vs duration (income statement) facts
- No RAG-ready output

### After: Normalized parquet tables

```
data/
  processed/sec/
    entity_master.parquet    # 1 row per company
    concepts.parquet         # dimension table: (taxonomy, concept) -> label, description
    facts.parquet            # event table: every datapoint with dedup ranking
    filings.parquet          # 1 row per unique filing
    manifest.json            # run stats + error log
  rag/
    sec_facts_index.parquet  # Tier-1 preferred facts as natural language sentences
```

---

## The 4 Normalized Tables

### 1. `entity_master.parquet`
One row per company. CIK is the anchor identity (not ticker).

| Column | Description |
|---|---|
| `cik` | 10-digit zero-padded string (e.g., "0000320193") |
| `entity_name` | Legal name from SEC filing |
| `last_seen_filing_date` | Most recent `filed_date` across all facts |
| `snapshot_date` | Date this parse was run |
| `partial` | True if source JSON was truncated and repaired |

### 2. `concepts.parquet`
Dimension table. No concept text is stored in the facts table — join here when needed.

| Column | Description |
|---|---|
| `taxonomy` | dei, us-gaap, ifrs-full, srt, invest |
| `concept` | XBRL concept name (e.g., "NetIncomeLoss") |
| `label` | Human-readable name |
| `description` | Full description of the metric |

### 3. `facts.parquet`
The main event table. Every XBRL datapoint, with dedup ranking and period semantics.

| Column | Description |
|---|---|
| `cik` | Links to entity_master |
| `taxonomy`, `concept` | Links to concepts table |
| `unit` | USD, shares, USD/shares, pure, etc. |
| `value` | The numeric value (float64) |
| `start_date` | Period start (empty for instant/balance-sheet items) |
| `end_date` | Period end (always present) |
| `fy`, `fp` | Fiscal year and period (Q1/Q2/Q3/FY) |
| `form` | Filing type (10-K, 10-Q, 8-K, etc.) |
| `filed_date` | When filed with SEC |
| `accession_number` | SEC accession number (links back to original filing) |
| `frame` | EDGAR calendar frame (debug only, optional) |
| **`period_type`** | **NEW:** `instant` or `duration` (Section 6) |
| **`period_key`** | **NEW:** Stable period key like `2023-FY` or `2023-Q1` |
| **`revision_rank`** | **NEW:** 1 = best version, 2+ = older/superseded (Section 7) |
| **`is_preferred`** | **NEW:** `true` if revision_rank == 1 |

### 4. `filings.parquet`
One row per unique filing, extracted from facts provenance.

| Column | Description |
|---|---|
| `cik` | Company |
| `accession_number` | Unique filing ID |
| `form` | 10-K, 10-Q, 8-K, etc. |
| `filed_date` | Date filed |

---

## New Features Explained

### Period Semantics (Section 6)
EDGAR mixes two types of facts:
- **Instant** (balance sheet): "Assets as of 2023-12-31" — only has `end_date`
- **Duration** (income/cash flow): "Revenue from 2023-01-01 to 2023-12-31" — has both `start_date` and `end_date`

Without this label, you'd accidentally sum balance sheet values across quarters or treat revenue as a point-in-time snapshot. The `period_type` column prevents this.

The `period_key` provides a stable identifier like `2023-FY` or `2023-Q2` instead of relying on EDGAR's optional `frame` field.

### Dedup Ranking (Section 7)
The same metric often appears multiple times across filings:
- Reported in 10-Q, then re-reported in 10-K for the same period
- Amended filings (10-K/A) supersede originals
- Restatements

The script **never deletes** any data. Instead, it ranks duplicates:
1. Latest `filed_date` wins (most recent filing has the best data)
2. Tie-breaker: 10-K beats 10-Q beats 8-K (form priority)

Result: `revision_rank=1` + `is_preferred=true` marks the best version. All others are kept for audit.

**For RAG:** only embed rows where `is_preferred = true`.

### RAG Index (Section 8)
Not every datapoint should be embedded — that creates noise. The script generates `sec_facts_index.parquet` containing natural language sentences for **Tier-1 preferred facts only**.

Tier-1 concepts (28 total):
- Balance sheet: Assets, Liabilities, Equity, Cash, etc.
- Income statement: Revenue, Net Income, EPS, Operating Income, etc.
- Cash flow: Operating/Investing/Financing cash flows
- Shares: Outstanding, Weighted Average

Example sentence:
> Apple Inc. reported Net Income (Loss) Attributable to Parent = 97,000,000,000 USD for period 2022-09-25 to 2023-09-30 (Form 10-K, filed 2023-11-03, accession 0000320193-23-000106).

These sentences are designed to embed well for semantic search — they contain the company name, metric, value, period, and full provenance.

### Truncated File Repair
50 of the 8,183 source files were truncated mid-download at exact MiB boundaries. The script:
1. Scans the raw JSON tracking bracket nesting
2. Finds the last complete structure
3. Closes all open brackets
4. Recovers 99.99%+ of the data
5. Marks the company as `partial=true` in entity_master

---

## How to Use

### Run the parser
```bash
# First run (creates all tables)
python stockrag/data/parse_company_facts.py

# Force re-run (overwrites existing output)
python stockrag/data/parse_company_facts.py --force

# Debug mode (stop on first error + verbose)
python stockrag/data/parse_company_facts.py --fail-fast --verbose
```

### Query the output (Python)
```python
import pyarrow.parquet as pq

# Load tables
entities = pq.read_table("stockrag/data/processed/sec/entity_master.parquet").to_pandas()
concepts = pq.read_table("stockrag/data/processed/sec/concepts.parquet").to_pandas()
facts = pq.read_table("stockrag/data/processed/sec/facts.parquet").to_pandas()
rag = pq.read_table("stockrag/data/rag/sec_facts_index.parquet").to_pandas()

# Find a company
apple = entities[entities["entity_name"].str.contains("Apple", case=False)]

# Get preferred facts only (deduped)
apple_facts = facts[(facts["cik"] == "0000320193") & (facts["is_preferred"])]

# Get revenue over time
revenue = apple_facts[apple_facts["concept"] == "Revenues"].sort_values("end_date")

# RAG sentences ready for embedding
apple_rag = rag[rag["cik"] == "0000320193"]
print(apple_rag["sentence"].iloc[0])
```

### Storage layout alignment
The output follows the directory structure from `update_data_readme.md` Section 3:
```
stockrag/data/
  processed/sec/      <-- normalized tables
  rag/                <-- embedding-ready index
```

---

## What's NOT Implemented Yet (from the checklist)

These are separate jobs, not part of the companyfacts parser:

- [ ] Shared path resolver with `.env` (Section 1)
- [ ] HTTP client with throttling/retry/caching (Section 10)
- [ ] SEC identity job to pull `company_tickers.json` for ticker mapping (Section 9.1)
- [ ] Daily filings discovery via EDGAR daily index (Section 9.2)
- [ ] Finnhub candles ingestion (Section 9.4)
- [ ] QA checks dashboard (Section 11)

These would be separate scripts under `stockrag/data/` or `stockrag/backend/data/`.
