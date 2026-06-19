"""Embeddings (M3) — an injectable `Embedder` interface plus a deterministic implementation.

Two implementations:

- **HashingEmbedder** — a deterministic, dependency-free hashing vectoriser. Near-duplicate texts
  (sharing most tokens) get high cosine similarity; distinct texts get low. It needs no model
  download, so it is the embedder for tests/CI and a safe fallback.
- **SentenceTransformerEmbedder** — the real local model (e.g. `BAAI/bge-small-en-v1.5`), imported
  lazily so this package loads even when `sentence-transformers` (and torch) are not installed.

The pipeline takes an `Embedder` by injection; pick the default with `get_embedder()`.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

from app.core.config import settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@runtime_checkable
class Embedder(Protocol):
    """Maps texts to unit-norm vectors. `dim` is the vector size; `name` identifies the model."""

    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class HashingEmbedder:
    """Deterministic bag-of-tokens hashing vectoriser (no model, no network).

    Each token is hashed to a dimension and accumulated; the vector is L2-normalised so cosine
    similarity reflects token overlap. Stable across processes (SHA-1 based), so dedup tests are
    reproducible.
    """

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or settings.hashing_embedding_dim
        self.name = f"hashing-{self.dim}"

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _tokenize(text):
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            # Signed contribution keeps unrelated texts closer to orthogonal.
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            # Empty/symbol-only text: a stable non-zero unit vector avoids div-by-zero in cosine.
            vec[0] = 1.0
            return vec
        return [x / norm for x in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


def get_embedder() -> Embedder:
    """Return the configured default embedder.

    `EMBEDDER=hashing` (or a missing `sentence-transformers`) yields the deterministic embedder;
    otherwise the real local model is loaded lazily.
    """
    if settings.embedder == "hashing":
        return HashingEmbedder()
    from app.embeddings.sentence_transformer import SentenceTransformerEmbedder

    return SentenceTransformerEmbedder(settings.embedding_model)


__all__ = ["Embedder", "HashingEmbedder", "get_embedder"]
