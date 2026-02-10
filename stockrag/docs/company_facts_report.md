# Data Report: SEC EDGAR Company Facts

## Dataset Overview

- **19,215 JSON files**, one per company (identified by CIK number)
- **18.42 GB total** on disk
- **2,647 files are empty/tiny** (<100 bytes) — these need to be skipped
- File sizes range from 0 KB to 8.9 MB (median ~495 KB, mean ~959 KB)

## JSON Structure (per file)

```json
{
  "cik": 320193,                    // SEC Central Index Key (unique company ID)
  "entityName": "Apple Inc.",       // Company legal name
  "facts": {
    "<taxonomy>": {
      "<concept>": {
        "label": "...",             // Human-readable name
        "description": "...",       // What this financial metric means
        "units": {
          "<unit>": [               // Array of time-series datapoints
            {
              "end": "2009-06-27",  // Period end date
              "start": "...",       // Period start date (only for duration metrics, NOT on instant/point-in-time)
              "val": 895816758,     // The actual value
              "accn": "...",        // SEC accession number (links to original filing)
              "fy": 2009,           // Fiscal year
              "fp": "Q3",           // Fiscal period (Q1/Q2/Q3/FY)
              "form": "10-Q",       // Filing type
              "filed": "2009-07-22",// Date filed with SEC
              "frame": "CY2009Q2I" // Calendar frame (optional, not always present)
            }
          ]
        }
      }
    }
  }
}
```

## Taxonomies Found

| Taxonomy | Frequency | Description |
|---|---|---|
| **us-gaap** | ~85% of files | US Generally Accepted Accounting Principles — the core financial data (balance sheet, income statement, cash flow) |
| **dei** | ~85% of files | Document & Entity Information — shares outstanding, public float |
| **srt** | ~14% of files | SEC Reporting Taxonomy — supplemental disclosures (very sparse, often 1-2 concepts) |
| **invest** | ~11% of files | Investment company taxonomy — mostly fund/investment entities |
| **ifrs-full** | ~3% of files | International Financial Reporting Standards — foreign filers (e.g., Grifols) |

## Key Metrics in us-gaap (most common across companies)

The top concepts appearing in 60-80%+ of companies:

- **Balance Sheet**: `Assets`, `LiabilitiesAndStockholdersEquity`, `StockholdersEquity`, `AssetsCurrent`, `LiabilitiesCurrent`, `RetainedEarningsAccumulatedDeficit`, `PropertyPlantAndEquipmentNet`
- **Income Statement**: `NetIncomeLoss`, `OperatingIncomeLoss`, `IncomeTaxExpenseBenefit`, `EarningsPerShareBasic`
- **Cash Flow**: `NetCashProvidedByUsedInOperatingActivities`, `...InvestingActivities`, `...FinancingActivities`
- **Share Info**: `CommonStockSharesOutstanding`, `WeightedAverageNumberOfSharesOutstandingBasic`

Total unique us-gaap concepts across all companies: **~5,600+** (though most companies have 200-500)

## Unit Types

| Unit | Meaning |
|---|---|
| `USD` | Dollar amounts |
| `USD/shares` | Per-share dollar amounts (EPS, dividends) |
| `shares` | Share counts |
| `pure` | Ratios/percentages (dimensionless) |
| `Year` | Time durations |
| `Store` | Custom units (rare, company-specific) |

## Filing Forms

- `10-K` — Annual report
- `10-Q` — Quarterly report
- `10-K/A` — Amended annual report
- `8-K` — Current report

---

# Parsing Plan

## Phase 1: Data Inventory & Cleaning

1. **Scan all 19,215 files** — identify and log the 2,647 empty/corrupt files
2. **Build a company manifest** — extract `(CIK, entityName, taxonomies_present, concept_count, date_range)` for every valid file
3. **Decide scope** — Do you want all 19K companies or a subset (e.g., S&P 500, specific sectors)? This affects everything downstream

## Phase 2: Schema Normalization

4. **Define a target schema** — Flatten the nested JSON into tabular records:
   - **Company table**: `cik, entity_name`
   - **Facts table**: `cik, taxonomy, concept, label, description, unit, end_date, start_date, value, fiscal_year, fiscal_period, form, filed_date, frame`
5. **Handle taxonomy differences** — `us-gaap` vs `ifrs-full` report similar things with different concept names. Decide: keep separate, or map IFRS concepts to GAAP equivalents?
6. **Handle duplicates** — The same metric often appears in both the 10-K and 10-Q for the same period (duplicate `val` for same `end` date). Define a dedup strategy (prefer `10-K` over `10-Q`, latest `filed` date wins, etc.)

## Phase 3: Parser Implementation

7. **Stream-based parsing** — 18 GB won't fit in memory at once. Process files one-at-a-time using `ijson` or standard `json` per-file (individual files max 9 MB, so per-file `json.load` is fine)
8. **Output format** — Write to Parquet (columnar, compressed, ~5-10x smaller than JSON). One Parquet file per batch or per taxonomy
9. **Parallelization** — Use `multiprocessing.Pool` or `concurrent.futures` to parse files in parallel across CPU cores. Each file is independent, so this is trivially parallelizable
10. **Progress tracking & error handling** — Log failures per-file, don't let one bad file crash the pipeline

## Phase 4: RAG-Specific Preparation

11. **Chunking strategy for embeddings** — Options:
    - **Per-concept chunks**: One text chunk = "Apple Inc. reported Assets of $352B for FY2023 (filed 10-K)" — good for specific financial lookups
    - **Per-company-period summary**: Aggregate a company's full financial snapshot for a quarter/year into one chunk — good for holistic questions
    - **Description chunks**: Embed the concept `label` + `description` for semantic concept matching
12. **Text generation** — Convert raw numbers into natural language sentences that embed well (e.g., "Apple Inc.'s net income for fiscal year 2023 was $97 billion, a decrease from $99.8 billion in FY2022")
13. **Metadata attachment** — Every chunk needs metadata for filtering: `cik, company_name, fiscal_year, fiscal_period, taxonomy, concept_category`

## Phase 5: Vector Store Ingestion

14. **Embed chunks** using your embedding model (scaffolded in `rag/embeddings.py`)
15. **Store in ChromaDB** (scaffolded in `chroma_db/` and `services/vector_db.py`) with metadata filters

---

# Things You May Have Missed

1. **2,647 empty files (~14%)** — significant chunk of the dataset is useless. Need to handle gracefully
2. **IFRS vs GAAP** — 3% of companies use IFRS (international). Their concept names are completely different. If you want to query across all companies, you need a mapping layer or separate handling
3. **Duplicate datapoints** — The same value gets re-reported across quarterly and annual filings. Without dedup, your RAG will have redundant/conflicting chunks
4. **`start` vs `end` dates** — Balance sheet items (point-in-time) only have `end`. Income/cash flow items (duration) have both `start` and `end`. This distinction matters for temporal queries
5. **The `frame` field is optional** — Not every entry has it. Don't rely on it as a primary key
6. **Concept names vary across companies** — While ~30 concepts are universal, companies use different subsets of the 5,600+ available concepts. A query about "R&D expenses" might map to `ResearchAndDevelopmentExpense` in one company and `ResearchAndDevelopmentExpenseSoftwareExcludingAcquiredInProcessCost` in another
7. **CIK-to-ticker mapping is missing** — Users will ask about "AAPL" or "Apple", not "CIK0000320193". You'll need an external mapping (SEC provides one via `company_tickers.json` from EDGAR)
8. **Temporal freshness** — The data spans from ~2008 to present. You need a strategy for time-aware retrieval (users asking "what is Apple's current revenue" should get the latest filing, not 2012)

---

# Open Questions

1. **Scope**: All 19K companies, or a specific subset (S&P 500, etc.)?
2. **Ticker mapping**: Do you already have a CIK-to-ticker/company-name mapping, or do we need to pull that from EDGAR?
3. **Target queries**: What kinds of questions should the RAG answer? (e.g., "What was Apple's revenue in 2023?" vs "Which companies had the highest profit margins?" vs "Compare AAPL and MSFT balance sheets") — this heavily influences chunking strategy
4. **Storage format preference**: Parquet intermediate? Or go straight from JSON to ChromaDB?
