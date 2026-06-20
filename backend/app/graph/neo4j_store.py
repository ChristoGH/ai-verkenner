"""Neo4j-backed GraphStore (M5) — idempotent MERGE writes + the convergence read.

Labels and relationship types come from the closed whitelists in `app.graph.util`, so building them
into Cypher (they cannot be parameterised) is safe. Every write is a `MERGE`, so projection is
idempotent: re-running adds no duplicate nodes/edges. Timestamps are written as tz-aware UTC.

This module raises on failure on purpose — the projection layer catches and degrades (the SQLite
record is already safe), exactly like the Qdrant path in M3.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from neo4j import Driver

from app.graph.store import (
    ConvergenceStat,
    GraphCounts,
    GraphLink,
    GraphNode,
    GraphView,
)
from app.graph.util import (
    ENTITY,
    EVENT,
    ITEM,
    NODE_LABELS,
    REL_TYPES,
    SOURCE,
    TOPIC,
    to_utc,
)


def _iso(value) -> str | None:
    """Neo4j temporal/native datetime → ISO-8601 UTC string (or None)."""
    if value is None:
        return None
    if hasattr(value, "to_native"):
        value = value.to_native()
    value = to_utc(value)
    return value.isoformat() if value is not None else None

logger = logging.getLogger(__name__)

# Node labels that get a uniqueness constraint on `uid` (the base labels — type labels piggyback).
_KEYED_LABELS = (ITEM, SOURCE, ENTITY, EVENT, TOPIC)


def _check_label(label: str) -> str:
    if label not in NODE_LABELS:
        raise ValueError(f"unknown node label: {label!r}")
    return label


def _check_rel(rel_type: str) -> str:
    if rel_type not in REL_TYPES:
        raise ValueError(f"unknown relationship type: {rel_type!r}")
    return rel_type


class Neo4jGraphStore:
    """Wraps a Neo4j driver. One session is opened per call (M5 scale)."""

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def _run(self, cypher: str, **params):
        with self._driver.session() as session:
            return list(session.run(cypher, **params))

    def ensure_schema(self) -> None:
        for label in _KEYED_LABELS:
            self._run(
                f"CREATE CONSTRAINT {label.lower()}_uid IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.uid IS UNIQUE"
            )

    def clear(self) -> None:
        self._run("MATCH (n) DETACH DELETE n")

    def merge_node(
        self, label: str, uid, props: dict | None = None, extra_labels: tuple[str, ...] = ()
    ) -> None:
        _check_label(label)
        cypher = f"MERGE (n:{label} {{uid: $uid}}) SET n += $props"
        for extra in extra_labels:
            cypher += f" SET n:{_check_label(extra)}"
        self._run(cypher, uid=uid, props=props or {})

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
        _check_rel(rel_type)
        _check_label(src_label)
        _check_label(dst_label)
        cypher = (
            f"MERGE (a:{src_label} {{uid: $src_uid}}) "
            f"MERGE (b:{dst_label} {{uid: $dst_uid}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) SET r += $props"
        )
        self._run(cypher, src_uid=src_uid, dst_uid=dst_uid, props=props or {})

    def convergence(self, since=None) -> list[ConvergenceStat]:
        since = to_utc(since)
        # Per entity, within the window: the distinct source names + distinct events (developments)
        # touching it (M5.5 hub-dampening inputs), plus mentions/recency/degree. Convergence,
        # recency and degree are all window-scoped so the signal reflects *recent* activity.
        cypher = (
            "MATCH (e:Entity) "
            "OPTIONAL MATCH (i:Item)-[m:MENTIONS]->(e) "
            "  WHERE $since IS NULL OR (m.ts IS NOT NULL AND m.ts >= $since) "
            "OPTIONAL MATCH (i)-[:FROM]->(s:Source) "
            "OPTIONAL MATCH (i)-[:IN_EVENT]->(ev:Event) "
            "WITH e, count(m) AS mentions, max(m.ts) AS last_ts, "
            "     collect(DISTINCT s.name) AS src_names_raw, "
            "     collect(DISTINCT ev.uid) AS ev_uids_raw "
            "WITH e, mentions, last_ts, "
            "     [x IN src_names_raw WHERE x IS NOT NULL] AS source_names, "
            "     size([x IN ev_uids_raw WHERE x IS NOT NULL]) AS event_count "
            "OPTIONAL MATCH (e)-[r:INTERACTS_WITH]-(:Entity) "
            "  WHERE $since IS NULL OR (r.ts IS NOT NULL AND r.ts >= $since) "
            "RETURN e.uid AS uid, source_names, size(source_names) AS distinct_sources, "
            "       mentions, last_ts, event_count, count(r) AS degree"
        )
        out: list[ConvergenceStat] = []
        for rec in self._run(cypher, since=since):
            last_ts = rec["last_ts"]
            out.append(
                ConvergenceStat(
                    entity_uid=rec["uid"],
                    distinct_sources=rec["distinct_sources"],
                    mentions=rec["mentions"],
                    degree=rec["degree"],
                    last_ts=last_ts.to_native() if hasattr(last_ts, "to_native") else last_ts,
                    event_count=rec["event_count"],
                    source_names=tuple(str(n) for n in rec["source_names"]),
                )
            )
        return out

    def counts(self) -> GraphCounts:
        nodes = self._run("MATCH (n) RETURN count(n) AS c")[0]["c"]
        edges = self._run("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
        return GraphCounts(nodes=nodes, edges=edges)

    def graph_view(self, *, limit=150, window_days=None, priority=None) -> GraphView:
        since = None
        if window_days and window_days > 0:
            since = to_utc(datetime.now(timezone.utc) - timedelta(days=window_days))
        entity_budget = max(1, limit // 2)

        # 1) Top entities by interaction degree (capped) — keeps the network legible.
        ent_rows = self._run(
            "MATCH (e:Entity) "
            "OPTIONAL MATCH (e)-[r:INTERACTS_WITH]-(:Entity) "
            "WITH e, count(r) AS deg ORDER BY deg DESC, e.uid LIMIT $n "
            "RETURN e.uid AS uid, e.name AS name, e.type AS type",
            n=entity_budget,
        )
        kept = [r["uid"] for r in ent_rows]
        kept_set = set(kept)
        nodes: list[GraphNode] = [
            GraphNode(id=f"entity:{r['uid']}", label=str(r["name"]), kind="entity", type=r["type"])
            for r in ent_rows
        ]
        node_ids = {n.id for n in nodes}
        links: list[GraphLink] = []

        if kept:
            # 2) Interactions among kept entities.
            for r in self._run(
                "MATCH (a:Entity)-[rel:INTERACTS_WITH]->(b:Entity) "
                "WHERE a.uid IN $kept AND b.uid IN $kept "
                "RETURN a.uid AS s, b.uid AS t, rel.ts AS ts",
                kept=kept,
            ):
                links.append(GraphLink(source=f"entity:{r['s']}", target=f"entity:{r['t']}",
                                       kind="interacts", ts=_iso(r["ts"])))

            # 3) Event → entity (an item in the event mentions a kept entity), within window.
            for r in self._run(
                "MATCH (ev:Event)<-[:IN_EVENT]-(i:Item)-[m:MENTIONS]->(e:Entity) "
                "WHERE e.uid IN $kept "
                "  AND ($priority IS NULL OR ev.priority_class = $priority) "
                "  AND ($since IS NULL OR (m.ts IS NOT NULL AND m.ts >= $since)) "
                "WITH ev, e, max(m.ts) AS ts "
                "RETURN ev.uid AS ev_uid, ev.title AS title, ev.priority_class AS pc, "
                "       e.uid AS ent_uid, ts",
                kept=kept, priority=priority, since=since,
            ):
                ev_id = f"event:{r['ev_uid']}"
                if ev_id not in node_ids and len(nodes) < limit:
                    nodes.append(GraphNode(id=ev_id, label=str(r["title"]), kind="event",
                                           priority_class=r["pc"]))
                    node_ids.add(ev_id)
                if ev_id in node_ids:
                    links.append(GraphLink(source=ev_id, target=f"entity:{r['ent_uid']}",
                                           kind="mentions", ts=_iso(r["ts"])))

        links = [l for l in links if l.source in node_ids and l.target in node_ids]
        total = self._run("MATCH (n) RETURN count(n) AS c")[0]["c"]
        return GraphView(nodes=nodes, links=links, truncated=total > len(nodes))
