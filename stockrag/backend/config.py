from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")


def _get_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value
    return default


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    llm_provider: str
    chroma_persist_dir: str
    api_port: int
    llm_model: str
    llm_max_tokens: int
    default_top_k: int
    retrieval_top_k: int
    embedding_model: str
    finnhub_api_key: str

    @property
    def chroma_dir(self) -> Path:
        return (BACKEND_DIR / self.chroma_persist_dir).resolve()


@lru_cache()
def get_settings() -> Settings:
    return Settings(
        gemini_api_key=_get_env("GEMINI_API_KEY", "GOOGLE_API_KEY", default=""),
        llm_provider=_get_env("LLM_PROVIDER", default="gemini"),
        chroma_persist_dir=_get_env("CHROMA_PERSIST_DIR", default="../chroma_db"),
        api_port=int(_get_env("API_PORT", default="8000")),
        llm_model=_get_env("LLM_MODEL", default="gemini-2.5-flash-lite"),
        llm_max_tokens=int(_get_env("LLM_MAX_TOKENS", default="1200")),
        default_top_k=int(_get_env("DEFAULT_TOP_K", default="5")),
        retrieval_top_k=int(_get_env("RETRIEVAL_TOP_K", default="20")),
        embedding_model=_get_env(
            "EMBEDDING_MODEL",
            default="sentence-transformers/all-MiniLM-L6-v2",
        ),
        finnhub_api_key=_get_env("FINNHUB_API_KEY", default=""),
    )


settings = get_settings()

GOOGLE_API_KEY = settings.gemini_api_key
LLM_MODEL = settings.llm_model
LLM_MAX_TOKENS = settings.llm_max_tokens
DEFAULT_TOP_K = settings.default_top_k
RETRIEVAL_TOP_K = settings.retrieval_top_k
EMBEDDING_MODEL = settings.embedding_model
CHROMA_DIR = settings.chroma_dir

PROFILES_COLLECTION = "company_profiles"
SNAPSHOTS_COLLECTION = "annual_snapshots"
FINNHUB_API_KEY = settings.finnhub_api_key

DESCRIPTIONS_COLLECTION = "company_descriptions"
