# StockRAG Data Layer README (EDGAR-first, RAG-ready)

This README consolidates the recommended changes to our data pipeline and storage format so we can implement clean, scalable, and RAG-friendly ingestion.

---

## 0) North Star

We want a data layer that is:

- **Authoritative** for fundamentals and filings
- **Traceable** (every number has a receipt back to a filing)
- **RAG-friendly** (minimal redundancy, fewer noisy chunks, consistent semantics)
- **Scalable** (incremental updates, partitioned storage, dedupe rules)

Core principle:
- **CIK is the anchor identity.** Ticker is metadata that can change.

Primary source-of-truth:
- SEC EDGAR for filings + XBRL facts

Optional market layer:
- Finnhub for price series and market context

Optional auxiliary sanity-check layer:
- Nasdaq symbol lists only for hygiene/enrichment, never as canonical truth.

---

## 1) Environment and Paths

We standardize file paths using `.env` with `python-dotenv`.

### `.env`
```env
ROOT=/absolute/path/to/project/root
```

All storage is under:
```
${ROOT}/stockrag/data/
```

---

## 2) Data Sources and What They’re For

### A) EDGAR (primary)
Use EDGAR for:
- Company identity anchored by CIK
- Filing metadata and filing timelines
- XBRL facts (dei + us-gaap + other taxonomies as needed)

### B) Finnhub (optional)
Use Finnhub for:
- OHLCV candles and market time series
- Event timing helpers (calendars) if needed
- Market context that EDGAR does not provide

### C) Nasdaq symbol lists (optional)
Use only for:
- Ticker hygiene checks
- Exchange-ish hints or coverage comparisons

Not for:
- “Universe of truth”
- Fundamental truth
- Any canonical mapping

---

## 3) Storage Layout (recommended)

Keep raw responses for auditability, build processed tables for querying, and create a slim RAG index.

```
stockrag/data/
  raw/
    sec/
      company_tickers.json
      company_tickers_exchange.json
      submissions/CIK##########.json
      companyfacts/CIK##########.json
      daily_index/YYYY/QTR#/master.YYYYMMDD.idx
    finnhub/
      candles/{ticker}/{YYYY-MM}.parquet
    aux/
      nasdaq/ (optional hygiene files)
  processed/
    sec/
      entity_master.parquet
      concepts.parquet
      facts.parquet
      filings.parquet
    market/
      prices.parquet (or partitioned by ticker/month)
  rag/
    sec_facts_index.parquet (or jsonl)
    embeddings/ (vector store artifacts)
  cache/
    http/
  logs/
```

---

## 4) Fix the Biggest Problem: Redundancy

### 4.1 Do not repeat concept metadata on every fact row
Concept `label` and `description` are concept-level, not datapoint-level.

**Instead of one giant table with repeated text, split into two:**

1) `concepts` (dimension table)
- (taxonomy, concept) → label, description

2) `facts` (event table)
- one row per numeric datapoint with provenance

This cuts file size, speeds reads, and reduces RAG noise.

### 4.2 Do not repeat company identity on every row
Do not store `entity_name` repeatedly in `facts`.
Keep it in `entity_master` and join when needed.

---

## 5) Processed Tables (contracts)

### 5.1 entity_master.parquet
One row per company (CIK):
- `cik` (10-digit, zero-padded string)
- `entity_name`
- `tickers` (array or delimited)
- `exchange` (if available)
- `last_seen_filing_date`
- `snapshot_date`
- optional: flags like `active_recent_filings`

### 5.2 filings.parquet
One row per filing:
- `cik`
- `accession_number`
- `form` (10-K, 10-Q, 8-K, etc.)
- `filed_date`
- optional: `report_date`, `primary_doc_url`, `items`

### 5.3 concepts.parquet
One row per concept:
- `taxonomy` (dei, us-gaap, etc.)
- `concept`
- `label`
- `description`

### 5.4 facts.parquet
One row per datapoint:
- `cik`
- `taxonomy`
- `concept`
- `unit`
- `value`
- `start_date` (nullable)
- `end_date` (required)
- `fy` (nullable)
- `fp` (nullable)
- `form` (nullable but recommended)
- `filed_date` (recommended)
- `accession_number` (recommended)
- optional: `frame` (debug only)

Add derived fields:
- `period_type`:
  - `instant` if start_date is null
  - `duration` if start_date is present
- `period_key` (our own stable key, not EDGAR frame):
  - suggested: `{fy}-{fp}` when available
  - else use `{end_date}` or `{start_date}-{end_date}`

---

## 6) Period Semantics: Instant vs Duration (must-have)

EDGAR mixes:
- Instant facts (balance sheet style, “as of end_date”)
- Duration facts (income/cashflow style, “start_date to end_date”)

If we don’t label this, we will accidentally:
- treat balances like flows
- sum point-in-time values across quarters

Rule:
- `start_date` present → duration
- `start_date` missing → instant

---

## 7) Deduplication, Restatements, and “Preferred Value” Policy

EDGAR can have multiple values for the same concept/unit/period across different filings (amendments, restatements).

We should **never delete** history, but we should **rank** it.

### 7.1 Define a stable grouping key
Group candidates by:
- `cik, taxonomy, concept, unit, start_date, end_date, fy, fp`

### 7.2 Ranking policy (simple, effective)
- Prefer the row with the latest `filed_date`
- If tie:
  - prefer 10-K over 10-Q for full-year values
  - otherwise keep both and mark a deterministic order

Add:
- `revision_rank` (1 = best)
- `is_preferred` (revision_rank == 1)

### 7.3 RAG rule
- Only embed/index rows where `is_preferred = true`
- Keep the rest for audit and “show all revisions” features

---

## 8) RAG Index Strategy (keep it slim)

We should not embed every datapoint. That turns the index into a landfill.

### 8.1 Concept tiers
- Tier 1 (always index): core financials + key DEI  
  shares outstanding, public float, revenues, net income, EPS, assets, liabilities, cash, operating cash flow, etc.
- Tier 2 (index on demand): sector/segment/disclosure-heavy tags
- Tier 3 (do not embed): noisy, rarely queried, weird units, or “pure” style values

### 8.2 Create “fact sentences” from structured facts
For each preferred Tier 1 fact:
- build a short sentence with provenance:
  - Company name or ticker (optional)
  - Concept label
  - Value + unit
  - Period (end_date, and start_date if duration)
  - Form + filed_date + accession_number (receipt)

Example template:
- `{entity_name} reported {label} = {value} {unit} for period ending {end_date} (Form {form}, filed {filed_date}, accession {accession_number}).`

Store these in:
- `stockrag/data/rag/sec_facts_index.parquet` (or jsonl)

Then embed that, not the entire `facts` table.

---

## 9) Update Workflows (incremental, scalable)

### 9.1 Daily identity refresh
- Download company tickers mappings
- Rebuild or upsert `entity_master`
- Record `snapshot_date`

### 9.2 Daily filings discovery
Preferred: use daily index to discover changes without polling every CIK.
- Parse daily index rows
- Upsert `filings.parquet`
- Identify CIKs with new relevant forms (ex: 10-K, 10-Q)

### 9.3 Fundamentals refresh
For each changed CIK:
- fetch updated `companyfacts/CIK##########.json`
- re-materialize facts for that CIK
- upsert into `facts.parquet`
- recompute `is_preferred` ranking for affected keys
- refresh RAG index rows for Tier 1 preferred facts

### 9.4 Market refresh (optional)
For tickers of interest:
- fetch daily candles
- partition by ticker/month
- join with EDGAR facts at query-time via entity_master mapping

---

## 10) Reliability Requirements (no surprises in production)

### 10.1 Rate limiting and headers
- Implement throttling and retries.
- Always send a real User-Agent.
- Respect published access policies for EDGAR and Finnhub.

### 10.2 Caching
- Cache HTTP responses by URL (ETag/Last-Modified if available)
- Keep raw JSON for audit, debugging, and reproducibility.

### 10.3 Retries
- Exponential backoff with jitter
- Handle 429 by backing off correctly

---

## 11) QA Checks (add these early)

Per company (CIK):
- count of facts ingested
- percent instant vs duration
- missing form/filed/accession coverage rate
- duplicate rate before ranking, after ranking
- top concepts by row count
- date range coverage

Global:
- number of CIKs updated today
- number of filings discovered today
- number of RAG index rows refreshed
- failure counts by endpoint/status code

---

## 12) Implementation Checklist (do this next)

- [ ] Create shared path resolver: `ROOT + relative_path`
- [ ] Create HTTP client: headers, throttling, retry, caching
- [ ] Build SEC identity job → `entity_master.parquet`
- [ ] Build filings discovery job → `filings.parquet`
- [ ] Build companyfacts ingestion job → `concepts.parquet` + `facts.parquet`
- [ ] Implement `period_type` + `period_key`
- [ ] Implement dedupe ranking → `is_preferred`
- [ ] Build RAG index generator (Tier allowlist + fact sentences)
- [ ] (Optional) Add Finnhub candles ingestion

---

## 13) What We Are NOT Doing (to stay sane)

- We are not using Nasdaq symbol data as a canonical universe.
- We are not embedding every datapoint.
- We are not trusting ticker as identity over CIK.
- We are not dropping historical revisions, only ranking them.

---

If we stick to this, the pipeline stays clean, explainable, and robust. The RAG layer gets smaller and sharper, and the structured layer stays truthful and auditable.
