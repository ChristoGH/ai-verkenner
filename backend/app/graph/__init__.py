"""Neo4j knowledge graph (M5) — a rebuildable derived index over the SQLite system of record.

Projects Items/Sources/Entities/Events/Topics + timestamped edges (PHASE_1_PLAN §3) from SQLite
into Neo4j with idempotent MERGEs, degrading (never crashing) when Neo4j is down. The graph also
answers the convergence read that feeds graph-aware ranking (`app/scoring/graph_signals.py`).

SQLite stays the source of truth: writes go to SQLite first (M3/M4), then project here best-effort;
`graph_reindex` rebuilds the graph purely from SQLite.
"""

from app.graph.memory import InMemoryGraph
from app.graph.neo4j_store import Neo4jGraphStore
from app.graph.projection import graph_reindex, project_event, project_new_events
from app.graph.store import (
    ConvergenceStat,
    GraphCounts,
    GraphLink,
    GraphNode,
    GraphStore,
    GraphView,
)

__all__ = [
    "GraphStore",
    "ConvergenceStat",
    "GraphCounts",
    "GraphNode",
    "GraphLink",
    "GraphView",
    "InMemoryGraph",
    "Neo4jGraphStore",
    "project_event",
    "project_new_events",
    "graph_reindex",
]
