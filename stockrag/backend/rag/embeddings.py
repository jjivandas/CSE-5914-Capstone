"""Sentence-transformer embedding function for ChromaDB."""

from __future__ import annotations

from typing import List

import chromadb
from chromadb import Documents, Embeddings
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def _get_model(model_name: str) -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(model_name)
    return _model


class STEmbeddingFunction(chromadb.EmbeddingFunction):
    """ChromaDB-compatible embedding function backed by sentence-transformers."""

    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name)

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002
        vecs = self._model.encode(list(input), normalize_embeddings=True, show_progress_bar=False)
        return vecs.tolist()
