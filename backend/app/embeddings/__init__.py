"""Embeddings (M3) — an injectable `Embedder` interface plus a deterministic implementation.

Two implementations:

- **HashingEmbedder** — a deterministic, dependency-free hashing vectoriser. Near-duplicate texts
  (sharing most tokens) get high cosine similarity; distinct texts get low. It needs no model
  download, so it is the embedder for tests/CI. It is **not an automatic fallback** — nothing
  selects it but an explicit `EMBEDDER=hashing`, because its width (256) differs from the shipped
  model's (384) and substituting one for the other silently would corrupt a live collection.
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

    `EMBEDDER=hashing` yields the deterministic embedder; any other value loads the real local
    model lazily.

    **There is no fall-back.** If `EMBEDDER` is not `hashing` and `sentence-transformers` is not
    installed, this RAISES `RuntimeError` (from `SentenceTransformerEmbedder.__init__`) rather
    than quietly returning `HashingEmbedder`. That is deliberate, not an oversight: the hashing
    embedder is 256-dimensional and the shipped model is 384-dimensional, so a silent fall-back
    would write vectors of the wrong width into an existing collection and corrupt the derived
    index. Failing loudly is the safe behaviour; choose the hashing embedder explicitly.
    """
    if settings.embedder == "hashing":
        return HashingEmbedder()
    from app.embeddings.sentence_transformer import SentenceTransformerEmbedder

    return SentenceTransformerEmbedder(settings.embedding_model)


__all__ = ["Embedder", "HashingEmbedder", "get_embedder"]
