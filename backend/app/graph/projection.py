"""Project the SQLite system of record into the Neo4j graph (M5).

SQLite is the source of truth; the graph is a **rebuildable derived index** (ADR 0001). So:

- `project_event` writes one Event's items/source/entities/relationships/topics with idempotent
  MERGEs (re-running changes nothing).
- `project_new_events` runs **after enrichment** in the pipeline, projecting only the new, enriched
  Events. It is **degrade-don't-crash**: a Neo4j failure is caught, the Event is left
  `projected=False` for a later retry, and the run continues — the SQLite record is never lost.
- `graph_reindex` rebuilds the whole graph purely from SQLite (clear → re-project everything),
  proving the derived index is disposable.

Graph schema follows PHASE_1_PLAN §3. `SIMILAR_TO` edges are intentionally omitted at M5 — we don't
persist pairwise similarity scores in SQLite (dedup uses Qdrant ANN transiently); they arrive with
the M6 graph endpoint if needed.
"""

from __future__ import annotations

import logging

from sqlmodel import Session, select

from app.graph.store import GraphStore
from app.graph.util import (
    ABOUT,
    ENTITY,
    EVENT,
    FROM,
    IN_EVENT,
    INTERACTS_WITH,
    ITEM,
    MENTIONS,
    SOURCE,
    TOPIC,
    entity_label,
    to_utc,
)
from app.models import EnrichedItem, Entity, Event, RawItem, Relationship, Source
from app.schemas.enrichment import normalise_entity_name

logger = logging.getLogger(__name__)


def _clean(props: dict) -> dict:
    """Drop None values so we don't write null properties."""
    return {k: v for k, v in props.items() if v is not None}


def project_event(store: GraphStore, session: Session, event: Event) -> None:
    """Project one enriched Event into the graph. Idempotent (MERGE). May raise (caller degrades)."""
    enriched = session.exec(
        select(EnrichedItem).where(EnrichedItem.event_id == event.id)
    ).first()
    items = session.exec(
        select(RawItem).where(RawItem.event_id == event.id).order_by(RawItem.id)
    ).all()
    if not items:
        return

    rep_id = event.representative_item_id or items[0].id

    # Event node.
    store.merge_node(EVENT, event.id, _clean({
        "title": event.title,
        "priority_class": enriched.priority_class if enriched else None,
        "category": enriched.category if enriched else None,
    }))

    # Items + their Source + IN_EVENT / FROM edges.
    for item in items:
        store.merge_node(ITEM, item.id, _clean({
            "title": item.title,
            "url": item.url,
            "source_name": item.source_name,
            "source_type": item.source_type,
            "published_at": to_utc(item.published_at),
            "content_hash": item.content_hash,
        }))
        store.merge_edge(IN_EVENT, src_label=ITEM, src_uid=item.id,
                         dst_label=EVENT, dst_uid=event.id)
        if item.source_id is not None:
            source = session.get(Source, item.source_id)
            if source is not None:
                store.merge_node(SOURCE, source.id, _clean({
                    "name": source.name, "url": source.url,
                    "source_type": source.source_type, "trust_level": source.trust_level,
                }))
                store.merge_edge(FROM, src_label=ITEM, src_uid=item.id,
                                 dst_label=SOURCE, dst_uid=source.id)

    # Entities + MENTIONS (from every item in the event → distinct-source convergence) + INTERACTS.
    rels = session.exec(
        select(Relationship).where(Relationship.event_id == event.id)
    ).all()
    entity_ids = {r.subject_entity_id for r in rels} | {r.object_entity_id for r in rels}
    for entity_id in entity_ids:
        entity = session.get(Entity, entity_id)
        if entity is None:
            continue
        extra = entity_label(entity.type)
        store.merge_node(
            ENTITY, entity.id,
            _clean({"name": entity.name, "normalised_name": entity.normalised_name,
                    "type": entity.type}),
            extra_labels=(extra,) if extra else (),
        )
        # Each item in the Event mentions the entity, stamped with the item's published time.
        for item in items:
            store.merge_edge(
                MENTIONS, src_label=ITEM, src_uid=item.id,
                dst_label=ENTITY, dst_uid=entity.id,
                props=_clean({"ts": to_utc(item.published_at)}),
            )

    for rel in rels:
        store.merge_edge(
            INTERACTS_WITH, src_label=ENTITY, src_uid=rel.subject_entity_id,
            dst_label=ENTITY, dst_uid=rel.object_entity_id,
            props=_clean({"ts": to_utc(rel.ts), "kind": rel.predicate}),
        )

    # Topics (from the enrichment's tags) → ABOUT from the representative item.
    if enriched:
        for tag in enriched.tags:
            topic_uid = normalise_entity_name(tag)
            if not topic_uid:
                continue
            store.merge_node(TOPIC, topic_uid, {"name": tag.strip()})
            store.merge_edge(ABOUT, src_label=ITEM, src_uid=rep_id,
                             dst_label=TOPIC, dst_uid=topic_uid)


def project_new_events(session: Session, store: GraphStore, new_rows: list[RawItem]) -> int:
    """Project the new, enriched Events introduced by this run. Degrade-don't-crash; idempotent.

    Returns the number of Events projected. A Neo4j failure stops further graph writes for this run
    (the affected Events stay `projected=False` for a later retry) but never raises.
    """
    # Distinct event ids in run order.
    event_ids: list[int] = []
    seen: set[int] = set()
    for row in new_rows:
        if row.event_id is not None and row.event_id not in seen:
            seen.add(row.event_id)
            event_ids.append(row.event_id)
    if not event_ids:
        return 0

    try:
        store.ensure_schema()
    except Exception as exc:  # noqa: BLE001 — Neo4j down; skip projection, keep SQLite safe
        logger.warning("neo4j unavailable; skipping graph projection this run: %s", exc)
        return 0

    projected = 0
    for event_id in event_ids:
        enriched = session.exec(
            select(EnrichedItem).where(EnrichedItem.event_id == event_id)
        ).first()
        if enriched is None or enriched.projected:
            continue  # not enriched yet, or already in the graph
        event = session.get(Event, event_id)
        if event is None:
            continue
        try:
            project_event(store, session, event)
        except Exception as exc:  # noqa: BLE001 — degrade; leave projected=False, stop graph writes
            logger.warning(
                "neo4j projection failed for event %s; left for re-projection: %s", event_id, exc
            )
            break
        enriched.projected = True
        session.add(enriched)
        session.commit()
        projected += 1
    return projected


def graph_reindex(session: Session, store: GraphStore, *, clear: bool = True) -> int:
    """Rebuild the whole Neo4j graph purely from SQLite. Returns Events projected.

    Proves the derived-index invariant: drop the graph, re-project every enriched Event. Raises on a
    Neo4j failure (reindex is a deliberate command, not the fail-safe run path).
    """
    store.ensure_schema()
    if clear:
        store.clear()

    enriched_rows = session.exec(select(EnrichedItem).order_by(EnrichedItem.event_id)).all()
    count = 0
    for enriched in enriched_rows:
        event = session.get(Event, enriched.event_id)
        if event is None:
            continue
        project_event(store, session, event)
        enriched.projected = True
        session.add(enriched)
        count += 1
    session.commit()
    logger.info("graph reindex: rebuilt Neo4j from %d enriched Event(s)", count)
    return count
