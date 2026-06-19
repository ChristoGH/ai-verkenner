"""Local sentence-transformers embedder (M3).

Kept in its own module with a **lazy** import so the rest of the app (and the test suite) never
needs `sentence-transformers`/torch installed. Install with `pip install -e ".[embeddings]"`.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedder:
    """Wraps a local `SentenceTransformer` model, returning unit-norm vectors."""

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise RuntimeError(
                "SentenceTransformerEmbedder requires the 'embeddings' extra: "
                'pip install -e ".[embeddings]"  (or set EMBEDDER=hashing)'
            ) from exc

        logger.info("loading local embedding model '%s'", model_name)
        self._model = SentenceTransformer(model_name)
        self.name = model_name
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> list[list[float]]:
        # normalize_embeddings=True → unit vectors so Qdrant cosine is well-behaved.
        vectors = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )
        return [v.tolist() for v in vectors]
