"""Tests for SQLite → Neo4j projection (M5).

Offline: the in-memory graph store mirrors Neo4j MERGE semantics; no live database. Covers
idempotency, the expected nodes/edges, graph reindex, and degrade-don't-crash on a write failure.
"""

from __future__ import annotations

from sqlmodel import select

from app.graph import InMemoryGraph, graph_reindex, project_new_events
from app.graph.util import (
    ABOUT,
    ENTITY,
    EVENT,
    FROM,
    IN_EVENT,
    INTERACTS_WITH,
    ITEM,
    MENTIONS,
    SOURCE,
    TOPIC,
)
from app.models import EnrichedItem, RawItem
from tests import graph_helpers as gh


def _seed_one_event(session):
    """One event, one source, one item, two entities + an interaction, one topic tag."""
    src = gh.add_source(session, "feedA")
    ev = gh.add_event(session, "GPT-5 release")
    item = gh.add_item(session, src, ev, title="OpenAI ships GPT-5", url="https://a/1")
    openai = gh.add_entity(session, "OpenAI", "org")
    gpt5 = gh.add_entity(session, "GPT-5", "model")
    gh.add_relationship(session, openai, "released", gpt5, event=ev, item=item)
    gh.add_enriched(session, ev, item, priority_class="operational_update", tags=["llm"])
    return ev, item, src, openai, gpt5


def _all_rows(session):
    return session.exec(select(RawItem)).all()


def test_projection_builds_expected_nodes_and_edges(session):
    ev, item, src, openai, gpt5 = _seed_one_event(session)
    g = InMemoryGraph()
    assert project_new_events(session, g, _all_rows(session)) == 1

    # Nodes (keyed by (label, uid)).
    assert (ITEM, item.id) in g.nodes
    assert (SOURCE, src.id) in g.nodes
    assert (EVENT, ev.id) in g.nodes
    assert (ENTITY, openai.id) in g.nodes
    assert (TOPIC, "llm") in g.nodes
    # Entity carries its type label.
    assert "Org" in g.nodes[(ENTITY, openai.id)]["labels"]
    assert "Model" in g.nodes[(ENTITY, gpt5.id)]["labels"]

    # Edges.
    assert (FROM, (ITEM, item.id), (SOURCE, src.id)) in g.edges
    assert (IN_EVENT, (ITEM, item.id), (EVENT, ev.id)) in g.edges
    assert (MENTIONS, (ITEM, item.id), (ENTITY, openai.id)) in g.edges
    assert (INTERACTS_WITH, (ENTITY, openai.id), (ENTITY, gpt5.id)) in g.edges
    assert (ABOUT, (ITEM, item.id), (TOPIC, "llm")) in g.edges
    # The interaction edge carries kind + ts.
    interact = g.edges[(INTERACTS_WITH, (ENTITY, openai.id), (ENTITY, gpt5.id))]
    assert interact["kind"] == "released"
    assert interact["ts"] is not None


def test_projection_is_idempotent(session):
    _seed_one_event(session)
    g = InMemoryGraph()
    rows = _all_rows(session)

    first = project_new_events(session, g, rows)
    counts_after_first = g.counts()
    second = project_new_events(session, g, rows)  # re-run

    assert first == 1
    assert second == 0  # already projected → nothing new
    assert g.counts() == counts_after_first  # MERGE added no duplicates

    # Even forcing a re-project (clear the flag) must not duplicate nodes/edges.
    for ei in session.exec(select(EnrichedItem)).all():
        ei.projected = False
        session.add(ei)
    session.commit()
    project_new_events(session, g, rows)
    assert g.counts() == counts_after_first


def test_projection_marks_events_projected(session):
    _seed_one_event(session)
    g = InMemoryGraph()
    project_new_events(session, g, _all_rows(session))
    assert all(ei.projected for ei in session.exec(select(EnrichedItem)).all())


def test_graph_reindex_rebuilds_from_sqlite_and_matches(session):
    _seed_one_event(session)
    live = InMemoryGraph()
    project_new_events(session, live, _all_rows(session))

    # Rebuild a *fresh* graph purely from SQLite.
    rebuilt = InMemoryGraph()
    count = graph_reindex(session, rebuilt)

    assert count == 1
    assert rebuilt.counts() == live.counts()
    assert set(rebuilt.nodes) == set(live.nodes)
    assert set(rebuilt.edges) == set(live.edges)


def test_sqlite_record_survives_neo4j_write_failure(session):
    """A Neo4j write failure must not raise or lose the SQLite record (ADR 0001)."""
    _seed_one_event(session)

    class BoomStore:
        def ensure_schema(self):
            return None

        def merge_node(self, *a, **k):
            raise RuntimeError("simulated neo4j outage")

        def merge_edge(self, *a, **k):
            raise RuntimeError("simulated neo4j outage")

    rows = _all_rows(session)
    projected = project_new_events(session, BoomStore(), rows)  # must not raise

    assert projected == 0
    # SQLite intact, and the event is flagged for re-projection (projected stays False).
    enriched = session.exec(select(EnrichedItem)).all()
    assert len(enriched) == 1
    assert enriched[0].projected is False
    assert len(session.exec(select(RawItem)).all()) == 1


def test_projection_skipped_when_event_not_enriched(session):
    # Items + event but no EnrichedItem → nothing to project (enrichment gates the graph).
    src = gh.add_source(session, "feedB")
    ev = gh.add_event(session, "unenriched")
    gh.add_item(session, src, ev, title="x", url="https://b/1")
    g = InMemoryGraph()
    assert project_new_events(session, g, _all_rows(session)) == 0
    assert g.counts().nodes == 0
