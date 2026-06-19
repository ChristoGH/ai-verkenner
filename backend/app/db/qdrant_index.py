"""Qdrant `items` collection helpers (M3) — the derived vector index.

Thin wrappers over the item-embedding collection used for semantic dedup (ANN cosine search) and,
later, GraphRAG retrieval. Payload is intentionally minimal: `{item_id, source, published_at}`.

Unlike the M2 `ping()`, these **raise** on failure. The persistence path catches them so a Qdrant
outage never loses the SQLite record (ADR 0001) — degrade to hash-only dedup, embed later.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from qdrant_client import QdrantClient, models

logger = logging.getLogger(__name__)

ITEMS_COLLECTION = "items"


@dataclass(frozen=True)
class Neighbour:
    """One ANN hit: the matched item id and its cosine similarity (1.0 = identical)."""

    item_id: int
    score: float


def ensure_collection(client: QdrantClient, dim: int) -> None:
    """Create the `items` collection (cosine) if it does not already exist."""
    if client.collection_exists(ITEMS_COLLECTION):
        return
    client.create_collection(
        collection_name=ITEMS_COLLECTION,
        vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
    )


def recreate_collection(client: QdrantClient, dim: int) -> None:
    """Drop and recreate the `items` collection — used by reindex to rebuild from SQLite."""
    if client.collection_exists(ITEMS_COLLECTION):
        client.delete_collection(ITEMS_COLLECTION)
    client.create_collection(
        collection_name=ITEMS_COLLECTION,
        vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
    )


def upsert_item(
    client: QdrantClient,
    item_id: int,
    vector: list[float],
    *,
    source: str,
    published_at: str | None,
) -> None:
    """Write/overwrite one item vector. The Qdrant point id is the SQLite RawItem id."""
    client.upsert(
        collection_name=ITEMS_COLLECTION,
        points=[
            models.PointStruct(
                id=item_id,
                vector=vector,
                payload={"item_id": item_id, "source": source, "published_at": published_at},
            )
        ],
    )


def search_neighbours(
    client: QdrantClient,
    vector: list[float],
    *,
    limit: int = 10,
    score_threshold: float | None = None,
    exclude_item_id: int | None = None,
) -> list[Neighbour]:
    """Return ANN hits at/above `score_threshold`, optionally excluding one item id."""
    hits = client.query_points(
        collection_name=ITEMS_COLLECTION,
        query=vector,
        limit=limit,
        score_threshold=score_threshold,
        with_payload=False,
    ).points
    out: list[Neighbour] = []
    for hit in hits:
        if exclude_item_id is not None and int(hit.id) == exclude_item_id:
            continue
        out.append(Neighbour(item_id=int(hit.id), score=float(hit.score)))
    return out
