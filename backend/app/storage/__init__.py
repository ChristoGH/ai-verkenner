"""Storage (M3): persist ingested items to SQLite, embed into Qdrant, dedup into Events.

SQLite is the system of record; Qdrant is a rebuildable derived index (ADR 0001). The public
surface:

- `hashing`     — deterministic identity (`dedup_key`) and content (`content_hash`) hashes.
- `repository`  — upsert Sources, persist new RawItems idempotently.
- `dedup`       — two-stage dedup → Event assignment, and `reindex` (rebuild Qdrant from SQLite).
- `pipeline`    — `ingest_and_store`, the end-to-end run path.
"""

from app.storage.dedup import assign_events, reindex
from app.storage.hashing import content_hash, dedup_key
from app.storage.pipeline import StoreRunResult, ingest_and_store
from app.storage.repository import persist_new_items, upsert_sources

__all__ = [
    "content_hash",
    "dedup_key",
    "upsert_sources",
    "persist_new_items",
    "assign_events",
    "reindex",
    "ingest_and_store",
    "StoreRunResult",
]
