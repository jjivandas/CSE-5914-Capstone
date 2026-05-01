# StockRAG

RAG-based stock recommendation system grounded in SEC EDGAR financial data,
served by a FastAPI backend, a React + Vite frontend, and a Google Gemini LLM.

A user asks a natural-language question ("suggest a semiconductor stock with
strong free cash flow"), the backend retrieves the most relevant company
profiles / descriptions / annual snapshots from a ChromaDB vector store
covering ~7,100 EDGAR-listed companies, and Gemini generates a grounded
recommendation with citations back to the underlying filings.

---

## Cold start (fresh clone)

The repo ships a one-shot orchestrator that sets up the Python venv, installs
both backend and frontend dependencies, prompts for the API keys it needs,
downloads the prebuilt Chroma vector store from a public Hugging Face dataset,
and then launches the backend (port 8000) and frontend (port 5173).

```bash
git clone https://github.com/jjivandas/CSE-5914-Capstone.git
cd CSE-5914-Capstone
npm run cold-start
```

What happens, in order (`scripts/cold-start.mjs`):

1. **Checks Node, Python, and `tar`** are on `PATH`.
2. **Creates `stockrag/backend/.venv`**, upgrades `pip`, and on Linux installs
   CPU-only PyTorch first (skips ~4 GB of CUDA wheels) before the rest of
   `stockrag/backend/requirements.txt`.
3. **Runs `npm install`** in `stockrag/frontend/`.
4. **Prompts for `stockrag/.env`** if missing — required: `GEMINI_API_KEY`
   ([get one](https://aistudio.google.com/apikey)); optional:
   `FINNHUB_API_KEY` for live prices. The example file at
   `stockrag/.env.example` lists every override.
5. **Bootstraps `stockrag/chroma_db/`** if empty: streams
   `chroma_db.tar.gz` (~256 MB) from the public HF dataset
   `KrishPatel0111/stockrag-chroma-db`, verifies SHA256 mid-stream against
   the published `.sha256`, extracts to `stockrag/chroma_db/`, then deletes
   the tarball. Skips the download if the directory already has data.
6. **Spawns the backend** (`uvicorn main:app --port 8000`) and frontend
   (`vite --port 5173`), wiring stdout/stderr through to your terminal.
   Ctrl-C tears both down together.

After it settles, open <http://localhost:5173>. The backend is reachable at
<http://localhost:8000> and a health check is at
<http://localhost:8000/api/health>.

### Required keys

| Var               | Purpose                      | Where to get one                     |
| ----------------- | ---------------------------- | ------------------------------------ |
| `GEMINI_API_KEY`  | LLM (Gemini 2.5 Flash Lite)  | <https://aistudio.google.com/apikey> |
| `FINNHUB_API_KEY` | (optional) live stock prices | <https://finnhub.io/register>        |

### Cold-start overrides

Set in your shell or `stockrag/.env`:

| Var                      | Effect                                                             |
| ------------------------ | ------------------------------------------------------------------ |
| `CHROMA_DB_URL`          | Use a different tarball URL (e.g. a personal HF dataset).          |
| `CHROMA_DB_SHA256_URL`   | Override the checksum URL (defaults to `${CHROMA_DB_URL}.sha256`). |
| `CHROMA_DB_URL=` (empty) | Skip the download entirely — start with an empty vector store.     |
| `API_PORT`               | Backend port (default `8000`).                                     |

### Re-running

The cold-start is idempotent: re-running it will reuse the existing venv,
node_modules, `.env`, and Chroma store. Delete any of those to force that
step to run from scratch.

---

## Project layout

```
CSE-5914-Capstone/
├── package.json               # defines `npm run cold-start`
├── scripts/cold-start.mjs     # orchestrator (venv, deps, .env, chroma fetch, spawn)
└── stockrag/
    ├── .env / .env.example    # backend + cold-start config
    ├── chroma_db/             # gitignored; populated by cold-start
    ├── backend/               # FastAPI + RAG pipeline
    │   ├── main.py            # app entry + CORS + router mount
    │   ├── config.py          # env loader + settings
    │   ├── api/
    │   │   ├── routes.py      # /api/health, /api/stats, /api/recommendations
    │   │   └── models.py      # Pydantic request/response models
    │   ├── rag/
    │   │   ├── embeddings.py  # SentenceTransformer wrapper for ChromaDB
    │   │   ├── vector_db.py   # ChromaDB persistent client + multi-collection search
    │   │   ├── retrieval.py   # query → ranked context blob
    │   │   ├── llm_service.py # Google Gemini via google-genai SDK
    │   │   └── pipeline.py    # full RAG: retrieve → format → generate
    │   └── requirements.txt
    ├── frontend/              # React 19 + Vite + Mantine
    ├── data/                  # raw + processed EDGAR data and pipeline scripts
    │   ├── parse_company_facts.py        # raw EDGAR JSON → 4 parquet tables
    │   ├── generate_company_embeddings.py # parquets → per-company RAG JSON
    │   └── index_into_chroma.py          # JSON → ChromaDB collections
    └── docs/
        ├── ARCHITECTURE.md
        ├── API.md
        ├── SETUP.md
        ├── DATA_PIPELINE_README.md
        ├── CHROMA_DB_BOOTSTRAP.md         # how the HF snapshot is published
        └── update_data_readme.md
```

---

## How it's built

### Data pipeline (already complete — output ships via the HF snapshot)

All 7,138 EDGAR-listed companies have been processed end-to-end:

1. **Raw download**: SEC EDGAR `companyfacts` JSON (one file per CIK).
2. **`stockrag/data/parse_company_facts.py`** — normalizes raw JSON into four
   parquet tables under `stockrag/data/processed/sec/` (`facts.parquet` is
   ~521 MB).
3. **`stockrag/data/generate_company_embeddings.py`** — joins facts with
   Wikipedia/Finnhub descriptions and writes one RAG-ready JSON per company
   into `stockrag/data/rag/companies/` (~6.6 GB), plus a master
   `companies_index.json`.
4. **`stockrag/data/index_into_chroma.py`** — embeds and indexes those JSONs
   into ChromaDB with three collections.

The resulting `stockrag/chroma_db/` is gitignored (511 MB) and rebuilding it
from raw EDGAR takes hours, which is why cold-start fetches a prebuilt
snapshot from Hugging Face instead.

### ChromaDB collections

| Collection             | Granularity              | Content                                               |
| ---------------------- | ------------------------ | ----------------------------------------------------- |
| `company_profiles`     | 1 doc per company        | profile text + first 2 sentences of description       |
| `company_descriptions` | 1 doc per company        | full Wikipedia/Finnhub prose description              |
| `annual_snapshots`     | up to 5 docs per company | per-fiscal-year financial summaries (5-year lookback) |

Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (overridable via
`EMBEDDING_MODEL`).

### RAG pipeline

A request to `/api/recommendations` flows:

1. **`rag/retrieval.py`** queries all three collections, merges + ranks
   results (default top-K = 20 retrieved, top-K = 5 returned).
2. **`rag/pipeline.py`** formats the merged hits into a context blob with
   per-source citations.
3. **`rag/llm_service.py`** calls Gemini 2.5 Flash Lite via the
   `google-genai` SDK with the prompt + context.
4. **`api/routes.py::_map_sources_to_recommendations`** projects the LLM
   output and the raw retrieval hits into the `RecommendationResponse`
   schema, including EDGAR URLs back to the source filings.

### API

Mounted under `/api` (see `stockrag/backend/main.py:20`):

| Method | Path                   | Purpose                                           |
| ------ | ---------------------- | ------------------------------------------------- |
| GET    | `/api/health`          | service health + Chroma connectivity              |
| GET    | `/api/stats`           | per-collection document counts                    |
| POST   | `/api/recommendations` | natural-language query → grounded recommendations |

See `stockrag/docs/API.md` for full request/response shapes.

### Frontend

`stockrag/frontend/` — React 19 + Vite 7 + Mantine. Talks to the backend via
axios at the URL configured in the frontend env. `npm run cold-start` runs
`vite` directly so HMR is on by default.

### LLM provider

Backend uses Google Gemini through the official `google-genai` SDK
(`stockrag/backend/rag/llm_service.py`). The provider is selectable via
`LLM_PROVIDER` / `LLM_MODEL` in `.env` but only Gemini is wired up today.
A 503 from Gemini is transient (Google-side overload) and currently bubbles
up as a 500 from `/api/recommendations`.

---

## Manual operations

### Run the backend on its own

```bash
cd stockrag/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Run the frontend on its own

```bash
cd stockrag/frontend
npm run dev
```

### Republish the Chroma snapshot

After re-running the data pipeline, repackage and re-upload the snapshot so
new clones pick it up automatically:

```bash
# from repo root, with huggingface_hub installed and `hf auth login` done
tar -czf chroma_db.tar.gz -C stockrag chroma_db
shasum -a 256 chroma_db.tar.gz | tee chroma_db.tar.gz.sha256

hf upload KrishPatel0111/stockrag-chroma-db chroma_db.tar.gz       --repo-type dataset
hf upload KrishPatel0111/stockrag-chroma-db chroma_db.tar.gz.sha256 --repo-type dataset

rm chroma_db.tar.gz chroma_db.tar.gz.sha256
```

The dataset URL stays the same, so the next cold-start anywhere picks up the
new index. Full notes (including the HF auto-gating gotcha and how to flip
visibility back to public via the REST API) live in
`stockrag/docs/CHROMA_DB_BOOTSTRAP.md`.

---

## Troubleshooting

- **Cold-start downloads 0 bytes / 401 GatedRepo from Hugging Face** — the
  dataset visibility flipped to gated. Verify with `curl -s
https://huggingface.co/api/datasets/KrishPatel0111/stockrag-chroma-db |
python3 -c "import sys,json; print(json.load(sys.stdin)['gated'])"`.
  Should print `False`. See `stockrag/docs/CHROMA_DB_BOOTSTRAP.md` for the
  REST-API fix.
- **`OSError: libcudart.so.13: file too short`** — corrupted/incomplete CUDA
  wheel from a previous install. Delete `stockrag/backend/.venv/` and re-run
  `npm run cold-start`; it will reinstall CPU-only torch on Linux.
- **Port 5173 or 8000 already in use** — a stale process from a prior run.
  `lsof -i :5173` / `lsof -i :8000` and kill the holder.
- **`GEMINI_API_KEY` not set** — re-run `npm run cold-start` (it'll prompt
  for missing keys), or edit `stockrag/.env` directly.
- **Empty recommendations on first query** — confirm the Chroma snapshot
  loaded: `du -sh stockrag/chroma_db` should be ~511 MB. If empty, re-run
  cold-start; if `CHROMA_DB_URL=` was set empty, unset it.

---

## Further reading

- `stockrag/docs/ARCHITECTURE.md` — component diagram and data flow
- `stockrag/docs/API.md` — full API reference
- `stockrag/docs/DATA_PIPELINE_README.md` — pipeline changelog
- `stockrag/docs/CHROMA_DB_BOOTSTRAP.md` — snapshot hosting + republish
- `stockrag/docs/SETUP.md` — manual (non-cold-start) setup
