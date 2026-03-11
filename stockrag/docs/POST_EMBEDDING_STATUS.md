# StockRAG — Project Status

> Last updated: 2026-03-11

---

## What Is Built

### Data Pipeline (`stockrag/data/`)

| File | Status | Description |
|------|--------|-------------|
| `parse_company_facts.py` | **Done** | Parses raw SEC EDGAR JSON → 4 normalised Parquet tables |
| `generate_company_embeddings.py` | **Done** | Builds per-company RAG JSON files; fetches Wikipedia/Finnhub descriptions |
| `index_into_chroma.py` | **Done** | Indexes company JSONs into ChromaDB (resumable, batched) |

**Outputs on disk:**

| Path | Contents |
|------|----------|
| `data/processed/sec/entity_master.parquet` | 7,138 companies (CIK, name, exchange, filing dates) |
| `data/processed/sec/facts.parquet` | ~521 MB normalised XBRL facts |
| `data/processed/sec/concepts.parquet` | Concept label dimension table |
| `data/processed/sec/filings.parquet` | Unique filing metadata |
| `data/rag/companies/` | 7,138 per-company JSON files (6.6 GB) |
| `data/rag/companies_index.json` | Master index of all companies |
| `data/rag/descriptions_cache.json` | Wikipedia/Finnhub description cache |
| `chroma_db/` | ChromaDB persistent vector store |

**ChromaDB collections:**

| Collection | Documents | Content |
|------------|-----------|---------|
| `company_profiles` | 7,138 | One financial summary per company |
| `annual_snapshots` | ~28,000 | Per fiscal-year structured financials (last 5 FY) |
| `company_descriptions` | ~7,138* | Wikipedia/Finnhub prose descriptions |

\* Descriptions collection populated after running `generate_company_embeddings.py --force` + `index_into_chroma.py --force`. If not yet re-run, the collection may be empty or partial.

---

### RAG Architecture (`stockrag/backend/rag/`, `stockrag/backend/services/`)

| File | Status | Description |
|------|--------|-------------|
| `backend/config.py` | **Done** | Central config — all paths, model names, constants |
| `backend/rag/embeddings.py` | **Done** | `STEmbeddingFunction` — SentenceTransformer (`all-MiniLM-L6-v2`) wrapper for ChromaDB |
| `backend/rag/retrieval.py` | **Done** | Queries ChromaDB, formats results as structured LLM context |
| `backend/rag/pipeline.py` | **Done** | Two-stage pipeline: query expansion → broad retrieval → LLM reranking → generation |
| `backend/services/vector_db.py` | **Done** | ChromaDB persistent client; searches 3 collections and merges by CIK |
| `backend/services/llm_service.py` | **Done** | Gemini client; `expand_query`, `rerank_candidates`, `stream_response`, `get_response` |

#### RAG Pipeline Flow

```
User Query
    │
    ▼
expand_query()          ← LLM rewrites query into SEC/financial search terms
    │
    ▼
ChromaDB search         ← top 20 candidates from each of 3 collections
(profiles + descriptions + snapshots)
    │
    ▼
rerank_candidates()     ← LLM picks top 10 most relevant companies by CIK
    │
    ▼
format_context()        ← builds structured text block for generation LLM
    │
    ▼
get_response() / stream_response()   ← Gemini generates final answer
    │
    ▼
Answer + source citations
```

---

### API (`stockrag/backend/api/`, `stockrag/backend/main.py`)

> Note: backend is owned by a separate team. Listed here for completeness.

| File | Status | Description |
|------|--------|-------------|
| `api/models.py` | Done | Pydantic schemas: `QueryRequest`, `QueryResponse`, `SourceDoc`, `HealthResponse` |
| `api/routes.py` | Done | `GET /api/health`, `POST /api/query`, `POST /api/query/stream` (SSE) |
| `main.py` | Done | FastAPI app entry, CORS middleware, startup API key check |
| `requirements.txt` | Done | All dependencies pinned |

---

### Demo (`stockrag/demo/`)

| File | Status | Description |
|------|--------|-------------|
| `demo/index.html` | **Done** | Single-file HTML/CSS/JS demo UI — no build step, open directly in browser |

---

## What Is Not Yet Done / Known Gaps

### High Priority

| Item | Location | Notes |
|------|----------|-------|
| Re-run description enrichment | `data/generate_company_embeddings.py` | Run `python3 generate_company_embeddings.py --force --finnhub-key KEY` — the previous run was killed before completing. Until this is done, the `company_descriptions` ChromaDB collection is empty and description-based retrieval (e.g. "GPU companies → NVIDIA") relies only on query expansion. |
| Re-index ChromaDB with descriptions | `data/index_into_chroma.py` | Run `python3 index_into_chroma.py --force` after the above step. |

### Medium Priority

| Item | Location | Notes |
|------|----------|-------|
| Frontend (React) | `stockrag/frontend/` | All `src/` files are empty stubs. A proper UI beyond the `demo/` HTML is not yet implemented. |
| Unit / integration tests | — | No test suite exists. The pipeline, retrieval, and embedding functions are untested. |
| Evaluation harness | — | No RAG evaluation (e.g. hit rate, MRR, faithfulness) is implemented. Hard to know retrieval quality without it. |

### Low Priority / Nice to Have

| Item | Notes |
|------|-------|
| Real-time stock price data | Current data is purely from SEC EDGAR filings (no live prices, no market cap) |
| Fact-sentence collection | `fact_sentences` ChromaDB collection defined but not indexed by default in `index_into_chroma.py` — enables precise per-fact retrieval |
| Streaming reranking | Current streaming path (`/api/query/stream`) blocks on reranking before emitting tokens; could stream while reranking in parallel |
| Query cache | Identical queries re-run the full pipeline each time |

---

## How to Run (Order of Operations)

```bash
# 1. Parse SEC EDGAR JSON → Parquet (only needed if raw data changes)
cd stockrag/data
python3 parse_company_facts.py

# 2. Generate per-company RAG JSONs + fetch descriptions
python3 generate_company_embeddings.py --force --finnhub-key YOUR_KEY

# 3. Index into ChromaDB
python3 index_into_chroma.py --force

# 4. Start the backend API
cd ../backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. Open the demo UI
open ../demo/index.html
```

**Required environment variables:**
```
GOOGLE_API_KEY=your_gemini_api_key
FINNHUB_API_KEY=your_finnhub_key   # only needed for step 2
```

---

## Key Design Decisions

- **Embedding model**: `all-MiniLM-L6-v2` (384-dim) — fast, small, good semantic similarity
- **LLM**: `gemini-2.5-flash-lite` — cheapest Gemini model with acceptable quality
- **Two-stage retrieval**: Cast a wide net (top 20) then LLM-rerank to top 10 — reduces irrelevant results vs pure vector search
- **Query expansion**: Translates user intent (e.g. "GPU companies") into SEC filing vocabulary before vector search — critical for matching EDGAR financial text
- **Three ChromaDB collections**: Separating profiles, descriptions, and snapshots allows tuned retrieval per doc type and avoids mixing financial numbers with prose
