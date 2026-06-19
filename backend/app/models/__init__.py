"""SQLModel persistence entities — the SQLite system of record.

SQLite is the source of truth (ADR 0001). Qdrant holds *derived* vectors and Neo4j (M5) a
*derived* graph; both are rebuildable from these rows. M3 covers `Source`, `RawItem`, `Event`;
M4 adds `EnrichedItem`, `Entity`, and `Relationship` (graph-ready, but written to SQLite only —
the Neo4j projection lands in M5). `Feedback` and `Digest` follow later.
"""

from app.models.entities import (
    EnrichedItem,
    Entity,
    Event,
    RawItem,
    Relationship,
    Source,
)

__all__ = [
    "Source",
    "RawItem",
    "Event",
    "EnrichedItem",
    "Entity",
    "Relationship",
]
