"""Central configuration — all paths and constants derived from file location."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# ── directory layout ──────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent
STOCKRAG_DIR = BACKEND_DIR.parent
DATA_DIR = STOCKRAG_DIR / "data"
RAG_DIR = DATA_DIR / "rag"
COMPANIES_DIR = RAG_DIR / "companies"
COMPANIES_INDEX = RAG_DIR / "companies_index.json"
CHROMA_DIR = STOCKRAG_DIR / "chroma_db"

# ── embedding model ───────────────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ── ChromaDB collections ───────────────────────────────────────────────────────
PROFILES_COLLECTION = "company_profiles"
SNAPSHOTS_COLLECTION = "annual_snapshots"
DESCRIPTIONS_COLLECTION = "company_descriptions"

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_MODEL = "gemini-2.5-flash-lite"
LLM_MAX_TOKENS = 4096

# ── retrieval ─────────────────────────────────────────────────────────────────
DEFAULT_TOP_K = 10      # final companies returned to the user
RETRIEVAL_TOP_K = 20    # candidates fetched from each ChromaDB collection before reranking
MAX_TOP_K = 20

# ── API keys (read at startup, never hard-coded) ──────────────────────────────
GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "")
