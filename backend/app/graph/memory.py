"""In-memory GraphStore (M5) — deterministic MERGE semantics, no Neo4j.

Used by the unit suite and as a reusable fake. Nodes are keyed by `(label, uid)` and edges by
`(rel_type, src, dst)`, so re-running a projection is naturally idempotent — exactly the property
Neo4j `MERGE` gives. `convergence` computes the same distinct-source/degree/recency stats the
Neo4j query returns.
"""

from __future__ import annotations

from datetime import datetime

from app.graph.store import ConvergenceStat, GraphCounts, GraphLink, GraphNode, GraphView
from app.graph.util import (
    ENTITY,
    EVENT,
    FROM,
    IN_EVENT,
    INTERACTS_WITH,
    ITEM,
    MENTIONS,
    SOURCE,
    to_utc,
)


def _iso(value) -> str | None:
    value = to_utc(value)
    return value.isoformat() if value is not None else None


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

    def graph_view(
        self, *, limit: int = 150, window_days: int | None = None, priority: str | None = None
    ) -> GraphView:
        # entity uid -> degree (within window), for "top entities" selection.
        degree: dict[object, int] = {}
        for (rel, src, dst), props in self.edges.items():
            if rel == INTERACTS_WITH:
                for end in (src, dst):
                    if end[0] == ENTITY:
                        degree[end[1]] = degree.get(end[1], 0) + 1

        entity_budget = max(1, limit // 2)
        top_entities = sorted(
            (uid for (label, uid) in self.nodes if label == ENTITY),
            key=lambda uid: (-degree.get(uid, 0), uid),
        )[:entity_budget]
        kept = set(top_entities)

        # item -> event (via IN_EVENT) for event↔entity mention links.
        item_event: dict[object, object] = {}
        for (rel, src, dst), _props in self.edges.items():
            if rel == IN_EVENT and src[0] == ITEM and dst[0] == EVENT:
                item_event[src[1]] = dst[1]

        nodes: list[GraphNode] = []
        node_ids: set[str] = set()
        for uid in top_entities:
            node = self.nodes[(ENTITY, uid)]
            nodes.append(GraphNode(
                id=f"entity:{uid}", label=str(node["props"].get("name", uid)),
                kind="entity", type=node["props"].get("type"),
            ))
            node_ids.add(f"entity:{uid}")

        links: list[GraphLink] = []
        # entity-entity interactions among kept entities.
        for (rel, src, dst), props in self.edges.items():
            if rel == INTERACTS_WITH and src[0] == ENTITY and dst[0] == ENTITY:
                if src[1] in kept and dst[1] in kept:
                    links.append(GraphLink(
                        source=f"entity:{src[1]}", target=f"entity:{dst[1]}",
                        kind="interacts", ts=_iso(props.get("ts")),
                    ))

        # event -> entity (an item in the event mentions a kept entity).
        seen_event_entity: set[tuple] = set()
        for (rel, src, dst), props in self.edges.items():
            if rel != MENTIONS or src[0] != ITEM or dst[0] != ENTITY:
                continue
            ent_uid = dst[1]
            if ent_uid not in kept:
                continue
            event_uid = item_event.get(src[1])
            if event_uid is None:
                continue
            ev_node = self.nodes.get((EVENT, event_uid))
            if ev_node is None:
                continue
            if priority is not None and ev_node["props"].get("priority_class") != priority:
                continue
            ev_id = f"event:{event_uid}"
            if ev_id not in node_ids and len(nodes) < limit:
                nodes.append(GraphNode(
                    id=ev_id, label=str(ev_node["props"].get("title", event_uid)),
                    kind="event", priority_class=ev_node["props"].get("priority_class"),
                ))
                node_ids.add(ev_id)
            edge_key = (event_uid, ent_uid)
            if ev_id in node_ids and edge_key not in seen_event_entity:
                seen_event_entity.add(edge_key)
                links.append(GraphLink(
                    source=ev_id, target=f"entity:{ent_uid}",
                    kind="mentions", ts=_iso(props.get("ts")),
                ))

        # Drop links whose endpoints we didn't keep.
        links = [l for l in links if l.source in node_ids and l.target in node_ids]
        return GraphView(nodes=nodes, links=links, truncated=len(self.nodes) > len(nodes))
