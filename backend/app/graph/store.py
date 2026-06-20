"""The `GraphStore` interface (M5).

A small, MERGE-shaped surface so projection logic is written once and tested against an in-memory
store, while production talks to Neo4j. Two implementations: `Neo4jGraphStore` (real Cypher) and
`InMemoryGraph` (deterministic, offline — used by the unit suite). The store also answers the
convergence read used by graph-aware ranking, so the signal can be computed without a live Neo4j.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ConvergenceStat:
    """Per-entity graph signal inputs: distinct sources, raw mentions, degree, recency."""

    entity_uid: int
    distinct_sources: int
    mentions: int
    degree: int
    last_ts: datetime | None


@dataclass(frozen=True)
class GraphCounts:
    """Coarse counts, for reindex/idempotency assertions."""

    nodes: int
    edges: int


@dataclass(frozen=True)
class GraphNode:
    """One node in the Cosmograph projection."""

    id: str                       # e.g. "entity:5" / "event:3"
    label: str
    kind: str                     # "entity" | "event"
    type: str | None = None       # entity type (org/model/...) when kind == "entity"
    priority_class: str | None = None  # when kind == "event"
    ts: str | None = None         # ISO timestamp for the Timeline (when known)


@dataclass(frozen=True)
class GraphLink:
    """One edge in the Cosmograph projection."""

    source: str
    target: str
    kind: str                     # "interacts" | "mentions"
    ts: str | None = None


@dataclass(frozen=True)
class GraphView:
    """A capped, readable projection for the frontend (events + top entities by default)."""

    nodes: list[GraphNode]
    links: list[GraphLink]
    truncated: bool = False


@runtime_checkable
class GraphStore(Protocol):
    """Idempotent MERGE-based graph writes + the convergence and view reads."""

    def ensure_schema(self) -> None:
        """Create node-key uniqueness constraints/indexes (idempotent)."""

    def clear(self) -> None:
        """Delete all nodes/edges — used by `graph_reindex` to rebuild purely from SQLite."""

    def merge_node(
        self, label: str, uid, props: dict | None = None, extra_labels: tuple[str, ...] = ()
    ) -> None:
        """MERGE a node by `(label, uid)`, set props, and union any extra labels."""

    def merge_edge(
        self,
        rel_type: str,
        *,
        src_label: str,
        src_uid,
        dst_label: str,
        dst_uid,
        props: dict | None = None,
    ) -> None:
        """MERGE an edge `(:src_label {uid})-[:rel_type]->(:dst_label {uid})` and set props."""

    def convergence(self, since: datetime | None = None) -> list[ConvergenceStat]:
        """Per-entity distinct-source / mention / degree / recency stats (within `since` window)."""

    def counts(self) -> GraphCounts:
        """Total node and edge counts."""

    def graph_view(
        self,
        *,
        limit: int = 150,
        window_days: int | None = None,
        priority: str | None = None,
    ) -> GraphView:
        """A capped events+entities projection for Cosmograph (top entities by degree)."""
