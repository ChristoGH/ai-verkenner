"""Graph schema constants + helpers (M5).

The node labels, relationship types, and entity-type → label mapping follow PHASE_1_PLAN §3.
Everything is a closed whitelist so the Neo4j store can build label/type into Cypher safely (labels
and relationship types cannot be parameterised in Cypher).

Timestamp convention: M4 stores `Relationship.ts` / `RawItem.published_at` as **naive UTC**. The
graph treats every timestamp as UTC — `to_utc` attaches `timezone.utc` to naive values so reads and
writes (and the convergence window) compare consistently.
"""

from __future__ import annotations

from datetime import datetime, timezone

# Node labels.
ITEM = "Item"
SOURCE = "Source"
ENTITY = "Entity"
EVENT = "Event"
TOPIC = "Topic"

NODE_LABELS = frozenset({ITEM, SOURCE, ENTITY, EVENT, TOPIC,
                         "Org", "Model", "Person", "Tool", "Concept"})

# Relationship types.
FROM = "FROM"
IN_EVENT = "IN_EVENT"
MENTIONS = "MENTIONS"
INTERACTS_WITH = "INTERACTS_WITH"
ABOUT = "ABOUT"
SIMILAR_TO = "SIMILAR_TO"

REL_TYPES = frozenset({FROM, IN_EVENT, MENTIONS, INTERACTS_WITH, ABOUT, SIMILAR_TO})

# Entity.type (lowercase, from EntityType) → the secondary Neo4j label.
ENTITY_TYPE_LABEL = {
    "org": "Org",
    "model": "Model",
    "person": "Person",
    "tool": "Tool",
    "concept": "Concept",
}


def entity_label(entity_type: str) -> str | None:
    """The `:Org`/`:Model`/… secondary label for an entity type, or None if unknown."""
    return ENTITY_TYPE_LABEL.get((entity_type or "").strip().lower())


def to_utc(value: datetime | None) -> datetime | None:
    """Return a tz-aware UTC datetime; naive values are assumed to already be UTC (M4 convention)."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
