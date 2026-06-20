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
    """Build a real cross-development convergence: 'RAG' across two horizon developments from two
    distinct sources (a genuine emerging signal under M5.5), plus an excluded operational update and
    a singleton horizon item that carries no convergence.
    """
    s1, s2, s3 = (gh.add_source(session, f"src{i}") for i in (1, 2, 3))
    rag = gh.add_entity(session, "RAG", "concept")

    # A1, A2: two horizon developments mentioning RAG, from two distinct sources → convergence.
    rag_events = []
    for i, src in enumerate((s1, s2)):
        ev = gh.add_event(session, f"RAG development {i}")
        item = gh.add_item(session, src, ev, title=f"New RAG approach {i}",
                           url=f"https://{src.name}/rag{i}")
        partner = gh.add_entity(session, f"RagPartner{i}", "tool")  # unique → not a driver
        gh.add_relationship(session, rag, "advances", partner, event=ev, item=item)
        gh.add_enriched(session, ev, item, priority_class="horizon_signal", tags=["rag"],
                        relevance=1, strategic_potential=4, hype=1)
        rag_events.append(ev)

    # B: operational_update, single source — must be EXCLUDED from /horizon.
    ev_b = gh.add_event(session, "Routine tool release")
    item_b = gh.add_item(session, s3, ev_b, title="Tool 1.2 released", url="https://src3/b")
    foo = gh.add_entity(session, "Foobar", "tool")
    bar = gh.add_entity(session, "Baztool", "tool")
    gh.add_relationship(session, foo, "uses", bar, event=ev_b, item=item_b)
    gh.add_enriched(session, ev_b, item_b, priority_class="operational_update", tags=["misc"],
                    relevance=3, strategic_potential=1, hype=1)

    # C: horizon_signal singleton — one development, one source → no convergence (ranks below RAG).
    ev_c = gh.add_event(session, "Lonely paper")
    item_c = gh.add_item(session, s3, ev_c, title="A niche paper", url="https://src3/c")
    lone = gh.add_entity(session, "LoneConcept", "concept")
    other = gh.add_entity(session, "OtherConcept", "concept")
    gh.add_relationship(session, lone, "relates_to", other, event=ev_c, item=item_c)
    gh.add_enriched(session, ev_c, item_c, priority_class="horizon_signal", tags=["niche"],
                    relevance=1, strategic_potential=4, hype=1)
    return rag_events, ev_b, ev_c


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
    tc, (rag_events, ev_b, ev_c), _store = client
    body = tc.get("/items").json()
    assert len(body) == 4
    # operational_update outranks horizon_signal (priority class first).
    assert body[0]["id"] == str(ev_b.id)
    assert body[0]["priority_class"] == "operational_update"
    # A converging RAG development carries its graph "why" (across 2 independent sources).
    a = next(it for it in body if it["id"] == str(rag_events[0].id))
    assert a["convergence"] == 2
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
    tc, (rag_events, ev_b, ev_c), _store = client
    body = tc.get("/items", params={"priority_class": "horizon_signal"}).json()
    assert {it["id"] for it in body} == {str(e.id) for e in rag_events} | {str(ev_c.id)}


def test_items_filter_by_entity(client):
    tc, (rag_events, ev_b, ev_c), _store = client
    body = tc.get("/items", params={"entity": "RAG"}).json()
    assert {it["id"] for it in body} == {str(e.id) for e in rag_events}


# ---- /horizon ----


def test_horizon_excludes_operational_and_ranks_converging_first(client):
    tc, (rag_events, ev_b, ev_c), _store = client
    body = tc.get("/horizon").json()
    ids = [it["id"] for it in body["items"]]
    rag_ids = {str(e.id) for e in rag_events}
    # ONLY the weak-signal quadrant — the operational_update is excluded.
    assert str(ev_b.id) not in ids
    assert set(ids) == rag_ids | {str(ev_c.id)}
    # A converging RAG development is on top, by graph convergence (NOT the class-first order).
    assert ids[0] in rag_ids
    top = body["items"][0]
    assert top["convergence"] == 2
    assert top["graph_score"] > 0
    # Evidence behind the `why` IS the driving entity's distinct sources (reconciled, M6 finding #3).
    assert set(top["contributing_sources"]) == {"src1", "src2"}
    assert "convergence" in top["graph_why"]
    # The singleton horizon item carries no convergence and ranks last.
    assert ids[-1] == str(ev_c.id)
    assert body["items"][-1]["convergence"] == 0


def test_horizon_degrades_without_graph(session):
    _seed(session)
    app.dependency_overrides[session_dep] = lambda: session
    app.dependency_overrides[graph_store_dep] = lambda: None  # Neo4j down
    try:
        body = TestClient(app).get("/horizon").json()
    finally:
        app.dependency_overrides.clear()
    assert body["graph_available"] is False
    # Still returns the weak-signal quadrant (the two RAG developments + the singleton).
    assert len(body["items"]) == 3
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
