"""SQLModel tables for the SQLite system of record (M3).

Schema notes (kept legible and forward-compatible):

- **Source** — one curated registry entry, upserted by its stable `name`.
- **RawItem** — one fetched item. Carries the **source URL intact** (core invariant), two hashes,
  and a nullable `event_id` FK. The two hashes are distinct on purpose:
    * `dedup_key`   — *identity* hash over (source, url, title, published). UNIQUE; this is what
                      makes re-runs idempotent (an already-stored item is recognised, not
                      re-inserted). Two different sources reporting the same story keep their own
                      rows — different URLs → different `dedup_key` — and are grouped by `event_id`.
    * `content_hash` — *content* fingerprint over normalised title+summary. NOT unique; it powers
                      stage-(a) of dedup (identical text → same event), and lets distinct sources
                      with byte-identical coverage collapse into one Event.
- **Event** — one real-world development covered by N RawItems.
- `embedded` — True once the item's vector is in Qdrant. A Qdrant write failure leaves it False
  (the SQLite record still persists); `reindex` / a later run can embed it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Source(SQLModel, table=True):
    """A curated source, mirrored from the YAML registry. Upserted by `name`."""

    __tablename__ = "source"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    source_type: str
    url: str
    repo_owner: str | None = None
    repo_name: str | None = None
    arxiv_query: str | None = None
    enabled: bool = True
    trust_level: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Event(SQLModel, table=True):
    """A cluster of near-duplicate RawItems describing one development."""

    __tablename__ = "event"

    id: int | None = Field(default=None, primary_key=True)
    title: str  # taken from the representative (first) item, for legibility
    representative_item_id: int | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class RawItem(SQLModel, table=True):
    """One fetched item. The source URL is preserved verbatim."""

    __tablename__ = "raw_item"

    id: int | None = Field(default=None, primary_key=True)
    source_id: int | None = Field(default=None, foreign_key="source.id", index=True)
    source_name: str
    source_type: str
    title: str
    url: str  # canonical link — ALWAYS preserved (core invariant)
    published_at: datetime | None = None
    summary: str | None = None

    dedup_key: str = Field(index=True, unique=True)  # identity → idempotency
    content_hash: str = Field(index=True)            # content fingerprint → stage-(a) dedup

    event_id: int | None = Field(default=None, foreign_key="event.id", index=True)
    embedded: bool = Field(default=False, index=True)  # vector present in Qdrant?
    created_at: datetime = Field(default_factory=_utcnow)
