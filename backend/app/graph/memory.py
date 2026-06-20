"""In-memory GraphStore (M5) — deterministic MERGE semantics, no Neo4j.

Used by the unit suite and as a reusable fake. Nodes are keyed by `(label, uid)` and edges by
`(rel_type, src, dst)`, so re-running a projection is naturally idempotent — exactly the property
Neo4j `MERGE` gives. `convergence` computes the same distinct-source/degree/recency stats the
Neo4j query returns.
"""

from __future__ import annotations

from datetime import datetime

from app.graph.store import ConvergenceStat, GraphCounts
from app.graph.util import ENTITY, FROM, INTERACTS_WITH, MENTIONS, SOURCE, to_utc


class InMemoryGraph:
    """A tiny property graph with MERGE-by-key writes and the convergence read."""

    def __init__(self) -> None:
        # (label, uid) -> {"labels": set[str], "props": dict}
        self.nodes: dict[tuple[str, object], dict] = {}
        # (rel_type, (src_label, src_uid), (dst_label, dst_uid)) -> props
        self.edges: dict[tuple, dict] = {}

    # ---- writes ----

    def ensure_schema(self) -> None:  # no-op; an in-memory dict needs no constraints
        return None

    def clear(self) -> None:
        self.nodes.clear()
        self.edges.clear()

    def _ensure_node(self, label: str, uid) -> dict:
        node = self.nodes.get((label, uid))
        if node is None:
            node = {"labels": {label}, "props": {}}
            self.nodes[(label, uid)] = node
        return node

    def merge_node(
        self, label: str, uid, props: dict | None = None, extra_labels: tuple[str, ...] = ()
    ) -> None:
        node = self._ensure_node(label, uid)
        node["labels"].update(extra_labels)
        if props:
            node["props"].update(props)

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
        # MERGE endpoints (mirror Neo4j MERGE — harmless if they already exist).
        self._ensure_node(src_label, src_uid)
        self._ensure_node(dst_label, dst_uid)
        key = (rel_type, (src_label, src_uid), (dst_label, dst_uid))
        edge = self.edges.setdefault(key, {})
        if props:
            edge.update(props)

    # ---- reads ----

    def convergence(self, since: datetime | None = None) -> list[ConvergenceStat]:
        since = to_utc(since)

        # Map each Item uid -> its Source uid (via FROM edges).
        item_source: dict[object, object] = {}
        for (rel, src, dst), _props in self.edges.items():
            if rel == FROM and src[0] == "Item" and dst[0] == SOURCE:
                item_source[src[1]] = dst[1]

        stats: list[ConvergenceStat] = []
        for (label, uid), _node in self.nodes.items():
            if label != ENTITY:
                continue

            sources: set[object] = set()
            mentions = 0
            last_ts: datetime | None = None
            degree = 0
            for (rel, src, dst), props in self.edges.items():
                if rel == MENTIONS and dst == (ENTITY, uid) and src[0] == "Item":
                    ts = to_utc(props.get("ts"))
                    if since is not None and (ts is None or ts < since):
                        continue
                    mentions += 1
                    src_uid = item_source.get(src[1])
                    if src_uid is not None:
                        sources.add(src_uid)
                    if ts is not None and (last_ts is None or ts > last_ts):
                        last_ts = ts
                elif rel == INTERACTS_WITH and (ENTITY, uid) in (src, dst):
                    ts = to_utc(props.get("ts"))
                    if since is not None and (ts is None or ts < since):
                        continue
                    degree += 1

            stats.append(
                ConvergenceStat(
                    entity_uid=uid,
                    distinct_sources=len(sources),
                    mentions=mentions,
                    degree=degree,
                    last_ts=last_ts,
                )
            )
        return stats

    def counts(self) -> GraphCounts:
        return GraphCounts(nodes=len(self.nodes), edges=len(self.edges))
