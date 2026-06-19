"""SQLModel persistence entities — the SQLite system of record (M3).

SQLite is the source of truth (ADR 0001). Qdrant holds *derived* vectors that are rebuildable
from these rows; nothing here depends on Qdrant. The M3 schema covers `Source`, `RawItem`, and
`Event`; `EnrichedItem`, `Entity`, `Relationship`, `Feedback`, and `Digest` follow in later
milestones.
"""

from app.models.entities import Event, RawItem, Source

__all__ = ["Source", "RawItem", "Event"]
