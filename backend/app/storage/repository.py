"""SQLite persistence: upsert Sources, persist new RawItems idempotently (M3).

SQLite is written **first** and is the source of truth. Persistence is idempotent: an item already
stored (same `dedup_key`) is skipped, so re-running a source never doubles rows.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import RawItem, Source
from app.schemas.raw_item import RawItem as RawItemSchema
from app.schemas.source import Source as SourceSchema
from app.storage.hashing import content_hash, dedup_key

logger = logging.getLogger(__name__)


def upsert_sources(session: Session, sources: list[SourceSchema]) -> dict[str, int]:
    """Insert or update Source rows (keyed by `name`). Returns {name: source_id}."""
    name_to_id: dict[str, int] = {}
    for src in sources:
        row = session.exec(select(Source).where(Source.name == src.name)).first()
        if row is None:
            row = Source(
                name=src.name,
                source_type=src.source_type.value,
                url=src.url,
                repo_owner=src.repo_owner,
                repo_name=src.repo_name,
                arxiv_query=src.arxiv_query,
                enabled=src.enabled,
                trust_level=src.trust_level.value,
            )
            session.add(row)
        else:
            row.source_type = src.source_type.value
            row.url = src.url
            row.repo_owner = src.repo_owner
            row.repo_name = src.repo_name
            row.arxiv_query = src.arxiv_query
            row.enabled = src.enabled
            row.trust_level = src.trust_level.value
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
    session.commit()

    for row in session.exec(select(Source)).all():
        if row.id is not None:
            name_to_id[row.name] = row.id
    return name_to_id


def persist_new_items(
    session: Session,
    items: list[RawItemSchema],
    source_ids: dict[str, int] | None = None,
) -> list[RawItem]:
    """Persist items not already stored. Returns the newly-inserted rows (with ids).

    Idempotent: items whose `dedup_key` already exists in SQLite — or are duplicated within this
    same batch — are skipped. Every stored row keeps its source URL verbatim.
    """
    source_ids = source_ids or {}

    # Compute keys once; drop in-batch duplicates so a feed repeating an item can't double-insert.
    keyed: list[tuple[str, RawItemSchema]] = []
    seen_in_batch: set[str] = set()
    for item in items:
        key = dedup_key(item.source_name, item.url, item.title, item.published_at)
        if key in seen_in_batch:
            continue
        seen_in_batch.add(key)
        keyed.append((key, item))

    if not keyed:
        return []

    # Which of these are already in SQLite?
    all_keys = [k for k, _ in keyed]
    existing: set[str] = set()
    # Chunk the IN() to stay well under SQLite's variable limit.
    for start in range(0, len(all_keys), 500):
        chunk = all_keys[start:start + 500]
        rows = session.exec(
            select(RawItem.dedup_key).where(RawItem.dedup_key.in_(chunk))
        ).all()
        existing.update(rows)

    new_rows: list[RawItem] = []
    for key, item in keyed:
        if key in existing:
            continue
        row = RawItem(
            source_id=source_ids.get(item.source_name),
            source_name=item.source_name,
            source_type=item.source_type.value,
            title=item.title,
            url=item.url,
            published_at=item.published_at,
            summary=item.summary,
            dedup_key=key,
            content_hash=content_hash(item.title, item.summary),
        )
        session.add(row)
        new_rows.append(row)

    session.commit()
    for row in new_rows:
        session.refresh(row)
    logger.info("persisted %d new item(s) (%d skipped as already stored)",
                len(new_rows), len(keyed) - len(new_rows))
    return new_rows
