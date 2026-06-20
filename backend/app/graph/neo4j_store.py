"""Neo4j-backed GraphStore (M5) — idempotent MERGE writes + the convergence read.

Labels and relationship types come from the closed whitelists in `app.graph.util`, so building them
into Cypher (they cannot be parameterised) is safe. Every write is a `MERGE`, so projection is
idempotent: re-running adds no duplicate nodes/edges. Timestamps are written as tz-aware UTC.

This module raises on failure on purpose — the projection layer catches and degrades (the SQLite
record is already safe), exactly like the Qdrant path in M3.
"""

from __future__ import annotations

import logging

from neo4j import Driver

from app.graph.store import ConvergenceStat, GraphCounts
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
        # Convergence/recency (via MENTIONS) and degree (via INTERACTS_WITH) are both scoped to the
        # same `since` window so the signal reflects *recent* graph activity consistently.
        cypher = (
            "MATCH (e:Entity) "
            "OPTIONAL MATCH (s:Source)<-[:FROM]-(i:Item)-[m:MENTIONS]->(e) "
            "  WHERE $since IS NULL OR (m.ts IS NOT NULL AND m.ts >= $since) "
            "WITH e, count(DISTINCT s) AS distinct_sources, count(m) AS mentions, "
            "     max(m.ts) AS last_ts "
            "OPTIONAL MATCH (e)-[r:INTERACTS_WITH]-(:Entity) "
            "  WHERE $since IS NULL OR (r.ts IS NOT NULL AND r.ts >= $since) "
            "RETURN e.uid AS uid, distinct_sources, mentions, last_ts, count(r) AS degree"
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
                )
            )
        return out

    def counts(self) -> GraphCounts:
        nodes = self._run("MATCH (n) RETURN count(n) AS c")[0]["c"]
        edges = self._run("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
        return GraphCounts(nodes=nodes, edges=edges)
