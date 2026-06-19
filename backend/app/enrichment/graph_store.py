"""Persist extracted entities + relationships to SQLite (M4).

Phase-1 entity resolution is **exact + normalised-string match only** — an entity is reused when
its `(normalised_name, type)` already exists, otherwise it is created. No fuzzy or embedding merge
(that is Phase 2); accepting some duplicate entities now is a deliberate trade.

The graph lives in SQLite at M4; M5 projects it into Neo4j. Relationships are NEON-style
timestamped triples — stamped with the source item's `published_at` when known.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlmodel import Session, select

from app.models import Entity, Relationship
from app.schemas.enrichment import EntityType, GraphExtractResult, normalise_entity_name

logger = logging.getLogger(__name__)


def resolve_entity(session: Session, name: str, type_: EntityType) -> Entity:
    """Return the existing entity for `(normalised_name, type)`, or create it."""
    normalised = normalise_entity_name(name)
    existing = session.exec(
        select(Entity)
        .where(Entity.normalised_name == normalised)
        .where(Entity.type == type_.value)
    ).first()
    if existing is not None:
        return existing
    entity = Entity(name=name.strip(), normalised_name=normalised, type=type_.value)
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


def persist_graph(
    session: Session,
    extract: GraphExtractResult,
    *,
    event_id: int,
    raw_item_id: int | None,
    ts: datetime | None,
    max_entities: int,
) -> tuple[int, int]:
    """Persist entities (capped) + the relationships among them. Returns (entities, relationships).

    A relationship is only stored if both its subject and object resolve to extracted entities, so
    extraction noise can't create dangling edges.
    """
    # Cap entities to contain sprawl; resolve each to a row, keyed by its declared name.
    by_name: dict[str, Entity] = {}
    for ent_in in extract.entities[:max_entities]:
        entity = resolve_entity(session, ent_in.name, ent_in.type)
        by_name[normalise_entity_name(ent_in.name)] = entity

    entity_count = len(by_name)
    relationship_count = 0
    for rel in extract.relationships:
        subject = by_name.get(normalise_entity_name(rel.subject))
        obj = by_name.get(normalise_entity_name(rel.object))
        if subject is None or obj is None:
            # Subject/object not among the extracted entities — skip rather than invent a node.
            logger.debug(
                "skipping relationship with unknown endpoint: %s -[%s]-> %s",
                rel.subject, rel.predicate, rel.object,
            )
            continue
        session.add(
            Relationship(
                subject_entity_id=subject.id,
                predicate=rel.predicate.strip(),
                object_entity_id=obj.id,
                ts=ts,
                event_id=event_id,
                raw_item_id=raw_item_id,
            )
        )
        relationship_count += 1

    session.commit()
    return entity_count, relationship_count
