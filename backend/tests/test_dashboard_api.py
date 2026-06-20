"""Tests for the M6 dashboard endpoints: /items, /graph, /horizon.

Offline: an in-memory SQLite session + an in-memory graph store injected via dependency overrides.
No live containers. Asserts the headline contracts — ranked Core Radar, the weak-signal quadrant
ranked by convergence (operational_update excluded, converging horizon_signal on top), capped graph.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.api.deps import graph_store_dep, session_dep
from app.graph import InMemoryGraph, project_new_events
from app.main import app
from app.models import RawItem
from tests import graph_helpers as gh


def _seed(session):
    """Build three events: a converging horizon signal, an isolated horizon signal, an op update."""
    # A: horizon_signal, 'RAG' touched by 3 distinct sources → strong convergence.
    ev_a = gh.add_event(session, "Quietly converging RAG")
    srcs = [gh.add_source(session, f"src{i}") for i in range(3)]
    items_a = [
        gh.add_item(session, srcs[i], ev_a, title="New RAG approach", url=f"https://src{i}/a")
        for i in range(3)
    ]
    rag = gh.add_entity(session, "RAG", "concept")
    qdrant = gh.add_entity(session, "Qdrant", "tool")
    gh.add_relationship(session, qdrant, "supports", rag, event=ev_a, item=items_a[0])
    gh.add_enriched(session, ev_a, items_a[0], priority_class="horizon_signal", tags=["rag"],
                    relevance=1, strategic_potential=4, hype=1)

    # B: operational_update, single source — must be EXCLUDED from /horizon.
    ev_b = gh.add_event(session, "Routine tool release")
    src_b = gh.add_source(session, "srcB")
    item_b = gh.add_item(session, src_b, ev_b, title="Tool 1.2 released", url="https://srcB/b")
    foo = gh.add_entity(session, "Foobar", "tool")
    bar = gh.add_entity(session, "Baztool", "tool")
    gh.add_relationship(session, foo, "uses", bar, event=ev_b, item=item_b)
    gh.add_enriched(session, ev_b, item_b, priority_class="operational_update", tags=["misc"],
                    relevance=3, strategic_potential=1, hype=1)

    # C: horizon_signal, isolated single source → weak convergence (ranks below A on /horizon).
    ev_c = gh.add_event(session, "Lonely paper")
    src_c = gh.add_source(session, "srcC")
    item_c = gh.add_item(session, src_c, ev_c, title="A niche paper", url="https://srcC/c")
    lone = gh.add_entity(session, "LoneConcept", "concept")
    other = gh.add_entity(session, "OtherConcept", "concept")
    gh.add_relationship(session, lone, "relates_to", other, event=ev_c, item=item_c)
    gh.add_enriched(session, ev_c, item_c, priority_class="horizon_signal", tags=["niche"],
                    relevance=1, strategic_potential=4, hype=1)
    return ev_a, ev_b, ev_c


@pytest.fixture
def client(session):
    store = InMemoryGraph()
    seeded = _seed(session)
    project_new_events(session, store, session.exec(select(RawItem)).all())

    app.dependency_overrides[session_dep] = lambda: session
    app.dependency_overrides[graph_store_dep] = lambda: store
    try:
        yield TestClient(app), seeded, store
    finally:
        app.dependency_overrides.clear()


# ---- /items ----


def test_items_returns_ranked_core_radar(client):
    tc, (ev_a, ev_b, ev_c), _store = client
    body = tc.get("/items").json()
    assert len(body) == 3
    # operational_update outranks horizon_signal (priority class first).
    assert body[0]["id"] == str(ev_b.id)
    assert body[0]["priority_class"] == "operational_update"
    # The converging horizon item carries its graph "why".
    a = next(it for it in body if it["id"] == str(ev_a.id))
    assert a["convergence"] == 3
    assert "convergence" in a["graph_why"]


def test_items_shape_has_all_fields(client):
    tc, _seeded, _store = client
    item = tc.get("/items").json()[0]
    for key in ("title", "source_name", "source_url", "published_at", "priority_class",
                "scores", "summary", "why_it_matters", "recommended_action", "graph_why"):
        assert key in item
    assert set(item["scores"]) == {
        "relevance", "novelty", "actionability", "strategic_potential", "hype"
    }
    assert item["source_url"].startswith("http")


def test_items_filter_by_priority_class(client):
    tc, (ev_a, ev_b, ev_c), _store = client
    body = tc.get("/items", params={"priority_class": "horizon_signal"}).json()
    assert {it["id"] for it in body} == {str(ev_a.id), str(ev_c.id)}


def test_items_filter_by_entity(client):
    tc, (ev_a, ev_b, ev_c), _store = client
    body = tc.get("/items", params={"entity": "RAG"}).json()
    assert {it["id"] for it in body} == {str(ev_a.id)}


# ---- /horizon ----


def test_horizon_excludes_operational_and_ranks_converging_first(client):
    tc, (ev_a, ev_b, ev_c), _store = client
    body = tc.get("/horizon").json()
    ids = [it["id"] for it in body["items"]]
    # ONLY the weak-signal quadrant — the operational_update is excluded.
    assert str(ev_b.id) not in ids
    assert set(ids) == {str(ev_a.id), str(ev_c.id)}
    # The converging horizon item is on top, by graph convergence (NOT the class-first order).
    assert ids[0] == str(ev_a.id)
    top = body["items"][0]
    assert top["convergence"] == 3
    assert top["graph_score"] > 0
    assert len(top["contributing_sources"]) == 3  # three independent sources
    assert "convergence" in top["graph_why"]


def test_horizon_degrades_without_graph(session):
    _seed(session)
    app.dependency_overrides[session_dep] = lambda: session
    app.dependency_overrides[graph_store_dep] = lambda: None  # Neo4j down
    try:
        body = TestClient(app).get("/horizon").json()
    finally:
        app.dependency_overrides.clear()
    assert body["graph_available"] is False
    # Still returns the weak-signal quadrant (just graph-less ordering).
    assert len(body["items"]) == 2
    assert all(it["priority_class"] in ("horizon_signal", "archive") for it in body["items"])


# ---- /graph ----


def test_graph_returns_capped_nodes_and_links(client):
    tc, _seeded, _store = client
    body = tc.get("/graph").json()
    assert body["available"] is True
    assert len(body["nodes"]) > 0
    kinds = {n["kind"] for n in body["nodes"]}
    assert "entity" in kinds
    # Links reference existing node ids.
    node_ids = {n["id"] for n in body["nodes"]}
    for link in body["links"]:
        assert link["source"] in node_ids
        assert link["target"] in node_ids


def test_graph_node_cap_is_respected(client):
    tc, _seeded, _store = client
    body = tc.get("/graph", params={"limit": 2}).json()
    assert len(body["nodes"]) <= 2


def test_graph_degrades_when_store_unavailable(session):
    app.dependency_overrides[graph_store_dep] = lambda: None
    try:
        body = TestClient(app).get("/graph").json()
    finally:
        app.dependency_overrides.clear()
    assert body["available"] is False
    assert body["nodes"] == [] and body["links"] == []
