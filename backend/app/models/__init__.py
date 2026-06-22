"""SQLModel persistence entities — the SQLite system of record.

SQLite is the source of truth (ADR 0001). Qdrant holds *derived* vectors and Neo4j (M5) a
*derived* graph; both are rebuildable from these rows. M3 covers `Source`, `RawItem`, `Event`;
M4 adds `EnrichedItem`, `Entity`, and `Relationship` (graph-ready, but written to SQLite only —
the Neo4j projection lands in M5). M7 adds `Feedback` (folded into ranking) and `Digest` (the
decision-oriented briefing composed over already-enriched Events).
"""

from app.models.entities import (
    Digest,
    EnrichedItem,
    Entity,
    Event,
    Feedback,
    RawItem,
    Relationship,
    RepoStarSnapshot,
    Source,
)

__all__ = [
    "Source",
    "RawItem",
    "Event",
    "EnrichedItem",
    "Entity",
    "Relationship",
    "RepoStarSnapshot",
    "Feedback",
    "Digest",
]
