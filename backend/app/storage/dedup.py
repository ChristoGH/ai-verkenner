"""Two-stage dedup → Events, and reindex (M3).

Two-stage dedup (borrows SemDeDup / news-dedup):
  (a) **content hash** — cheap exact-content match (collapses byte-identical coverage);
  (b) **Qdrant ANN cosine ≥ τ** — catches semantic near-duplicates worded differently.
Survivors are grouped so that one `Event` = one real-world development covered by N items.

Degrade-don't-crash (ADR 0001): if Qdrant is unreachable, dedup falls back to **hash-only** —
stage (a) plus new events — and items are left `embedded=False` to be embedded later. The SQLite
record is never lost because it is written before any Qdrant call.

Stable & idempotent: only *new* (unevented) items are assigned. A re-run produces no new rows, so
existing Event assignments don't move.
"""

from __future__ import annotations

import logging

from qdrant_client import QdrantClient
from sqlmodel import Session, select

from app.db import qdrant_index
from app.embeddings import Embedder
from app.models import Event, RawItem
from app.storage.hashing import embedding_text

logger = logging.getLogger(__name__)


def _published_iso(item: RawItem) -> str | None:
    return item.published_at.isoformat() if item.published_at else None


def _sort_key(item: RawItem) -> tuple[str, int]:
    """Deterministic processing order: oldest first, then id."""
    return (_published_iso(item) or "", item.id or 0)


def _event_via_content_hash(session: Session, item: RawItem) -> int | None:
    """Stage (a): an already-evented item with the same content hash shares its Event."""
    rows = session.exec(
        select(RawItem)
        .where(RawItem.content_hash == item.content_hash)
        .where(RawItem.event_id.is_not(None))
        .where(RawItem.id != item.id)
    ).all()
    if not rows:
        return None
    # Smallest event id = the earliest cluster, for a stable choice.
    return min(r.event_id for r in rows if r.event_id is not None)


def _event_via_ann(
    session: Session,
    client: QdrantClient,
    vector: list[float],
    item: RawItem,
    tau: float,
) -> int | None:
    """Stage (b): the highest-scoring indexed neighbour at/above τ donates its Event."""
    neighbours = qdrant_index.search_neighbours(
        client, vector, limit=10, score_threshold=tau, exclude_item_id=item.id
    )
    for neighbour in neighbours:  # already sorted best-first by Qdrant
        other = session.get(RawItem, neighbour.item_id)
        if other is not None and other.event_id is not None:
            return other.event_id
    return None


def _new_event(session: Session, item: RawItem) -> int:
    event = Event(title=item.title, representative_item_id=item.id)
    session.add(event)
    session.commit()
    session.refresh(event)
    assert event.id is not None
    return event.id


def assign_events(
    session: Session,
    items: list[RawItem],
    *,
    qdrant_client: QdrantClient | None,
    embedder: Embedder,
    tau: float,
) -> None:
    """Assign each new item to an Event via two-stage dedup, then index its vector.

    Never raises on a Qdrant problem — degrades to hash-only and leaves the item `embedded=False`.
    """
    if not items:
        return

    qdrant_ok = qdrant_client is not None
    if qdrant_ok:
        try:
            qdrant_index.ensure_collection(qdrant_client, embedder.dim)
        except Exception as exc:  # noqa: BLE001 — degrade to hash-only
            logger.warning("qdrant unavailable; dedup degrades to hash-only: %s", exc)
            qdrant_ok = False

    for item in sorted(items, key=_sort_key):
        # Embed once (used for both ANN search and indexing) when Qdrant is usable.
        vector: list[float] | None = None
        if qdrant_ok:
            try:
                vector = embedder.embed([embedding_text(item.title, item.summary)])[0]
            except Exception as exc:  # noqa: BLE001 — never let embedding crash a run
                logger.warning("embedding failed for item %s: %s", item.id, exc)

        # Stage (a): exact content hash.
        event_id = _event_via_content_hash(session, item)

        # Stage (b): semantic ANN (only if we have a vector and Qdrant is up).
        if event_id is None and qdrant_ok and vector is not None:
            try:
                event_id = _event_via_ann(session, qdrant_client, vector, item, tau)
            except Exception as exc:  # noqa: BLE001 — degrade to hash-only for the rest of the run
                logger.warning("qdrant search failed; degrading to hash-only: %s", exc)
                qdrant_ok = False

        # Otherwise this item starts a new Event.
        if event_id is None:
            event_id = _new_event(session, item)

        item.event_id = event_id

        # Index the vector so later items in this run can match it. A write failure must NOT lose
        # the SQLite record — log, leave embedded=False, keep going.
        if qdrant_ok and vector is not None:
            try:
                qdrant_index.upsert_item(
                    qdrant_client,
                    item.id,
                    vector,
                    source=item.source_name,
                    published_at=_published_iso(item),
                )
                item.embedded = True
            except Exception as exc:  # noqa: BLE001 — the SQLite record stands regardless
                logger.warning(
                    "qdrant upsert failed for item %s; left embeddable-later: %s", item.id, exc
                )
                qdrant_ok = False

        session.add(item)

    session.commit()


def reindex(
    session: Session,
    *,
    qdrant_client: QdrantClient,
    embedder: Embedder,
    batch_size: int = 128,
) -> int:
    """Rebuild the Qdrant `items` collection purely from SQLite. Returns items indexed.

    Proves the derived-index invariant: drop the collection, re-embed every RawItem, write it back.
    """
    qdrant_index.recreate_collection(qdrant_client, embedder.dim)

    rows = session.exec(select(RawItem).order_by(RawItem.id)).all()
    indexed = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        vectors = embedder.embed([embedding_text(r.title, r.summary) for r in batch])
        for row, vector in zip(batch, vectors):
            qdrant_index.upsert_item(
                qdrant_client,
                row.id,
                vector,
                source=row.source_name,
                published_at=_published_iso(row),
            )
            row.embedded = True
            session.add(row)
            indexed += 1
    session.commit()
    logger.info("reindex: rebuilt qdrant '%s' from %d SQLite item(s)",
                qdrant_index.ITEMS_COLLECTION, indexed)
    return indexed
