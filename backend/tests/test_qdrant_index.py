"""Tests for the Qdrant items-collection helpers (M3 + the M6 dim self-heal)."""

from __future__ import annotations

from qdrant_client import QdrantClient, models

from app.db import qdrant_index


def _client() -> QdrantClient:
    return QdrantClient(location=":memory:")


def test_ensure_collection_creates_at_requested_dim():
    client = _client()
    qdrant_index.ensure_collection(client, 16)
    assert qdrant_index._existing_dim(client) == 16


def test_ensure_collection_is_idempotent_for_matching_dim():
    client = _client()
    qdrant_index.ensure_collection(client, 16)
    # Seed a point so we can prove the collection was NOT recreated (point survives).
    qdrant_index.upsert_item(client, 1, [0.0] * 16, source="s", published_at=None)
    qdrant_index.ensure_collection(client, 16)
    assert client.get_collection(qdrant_index.ITEMS_COLLECTION).points_count == 1


def test_ensure_collection_self_heals_on_dim_mismatch():
    # A stale collection at the wrong dim (e.g. a different embedder) is dropped + recreated —
    # this is the M6 real-data smoke finding (hashing 256 vs sentence-transformers 384).
    client = _client()
    client.create_collection(
        collection_name=qdrant_index.ITEMS_COLLECTION,
        vectors_config=models.VectorParams(size=256, distance=models.Distance.COSINE),
    )
    qdrant_index.upsert_item(client, 1, [0.0] * 256, source="s", published_at=None)

    qdrant_index.ensure_collection(client, 384)  # embedder now produces 384-dim vectors

    assert qdrant_index._existing_dim(client) == 384
    # Recreated → the stale 256-dim point is gone, and 384-dim upserts now work.
    assert client.get_collection(qdrant_index.ITEMS_COLLECTION).points_count == 0
    qdrant_index.upsert_item(client, 2, [0.1] * 384, source="s", published_at=None)
    assert client.get_collection(qdrant_index.ITEMS_COLLECTION).points_count == 1
