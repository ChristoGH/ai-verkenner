"""Tests for graph-aware ranking (M5): convergence promotes, priority class + hype invariants hold.

Offline: in-memory graph + SQLite. The headline check — a converging entity ranks above an isolated
item WITHOUT changing its priority class, and hype still demotes.
"""

from __future__ import annotations

from sqlmodel import select

from app.graph import InMemoryGraph, project_new_events
from app.models import EnrichedItem, RawItem
from app.scoring.graph_signals import compute_signals
from app.scoring.ranking import rank, rank_with_graph
from tests import graph_helpers as gh


def _project_all(session):
    g = InMemoryGraph()
    project_new_events(session, g, session.exec(select(RawItem)).all())
    return g


def _converging_vs_isolated(session, *, conv_hype=1, iso_hype=1):
    """Event A: entity touched by 4 distinct sources. Event B: a single-source isolated item.

    Both share the same priority class and salient scores (only hype may differ), so any rank
    difference is purely the graph signal.
    """
    ev_a = gh.add_event(session, "RAG convergence")
    sources = [gh.add_source(session, f"src{i}") for i in range(4)]
    items_a = [
        gh.add_item(session, sources[i], ev_a, title="New RAG tooling", url=f"https://src{i}/a")
        for i in range(4)
    ]
    rag = gh.add_entity(session, "RAG", "concept")
    qdrant = gh.add_entity(session, "Qdrant", "tool")
    gh.add_relationship(session, qdrant, "supports", rag, event=ev_a, item=items_a[0])
    ei_a = gh.add_enriched(session, ev_a, items_a[0], priority_class="operational_update",
                           tags=["rag"], hype=conv_hype)

    ev_b = gh.add_event(session, "Isolated")
    src_b = gh.add_source(session, "srcB")
    item_b = gh.add_item(session, src_b, ev_b, title="Unrelated note", url="https://srcB/b")
    foo = gh.add_entity(session, "Foobar", "tool")
    bar = gh.add_entity(session, "Baztool", "tool")
    gh.add_relationship(session, foo, "uses", bar, event=ev_b, item=item_b)
    ei_b = gh.add_enriched(session, ev_b, item_b, priority_class="operational_update",
                           tags=["misc"], hype=iso_hype)
    return ev_a, ev_b, ei_a, ei_b


def test_convergence_promotes_without_changing_priority_class(session):
    ev_a, ev_b, ei_a, ei_b = _converging_vs_isolated(session)
    g = _project_all(session)

    eis = session.exec(select(EnrichedItem)).all()
    signals = compute_signals(session, g, [e.event_id for e in eis], window_days=0)

    # The converging event has a strictly larger signal.
    assert signals[ev_a.id].convergence == 4
    assert signals[ev_b.id].convergence <= 1
    assert signals[ev_a.id].score > signals[ev_b.id].score
    assert "convergence" in signals[ev_a.id].why

    ordered = rank_with_graph(eis, signals)
    assert ordered[0].event_id == ev_a.id      # convergence promotes it to the top
    # …but its priority class is unchanged (still what compute_priority_class gave).
    assert ei_a.priority_class == "operational_update"
    assert {e.priority_class for e in ordered} == {"operational_update"}
    # Without the graph signal the two are a salience tie (graph is the only differentiator).
    assert {e.event_id for e in rank(eis)} == {ev_a.id, ev_b.id}


def test_hype_still_demotes_when_graph_signal_is_equal(session):
    # Same convergence story, but event A is high-hype (noise). With an equal graph signal, hype
    # must still demote A below the low-hype B.
    ev_a, ev_b, ei_a, ei_b = _converging_vs_isolated(session, conv_hype=5, iso_hype=0)
    g = _project_all(session)
    eis = session.exec(select(EnrichedItem)).all()

    # Force identical graph signals so ONLY hype differs.
    from app.scoring.graph_signals import GraphSignal
    equal = {e.event_id: GraphSignal(convergence=2, score=2.0, why="x") for e in eis}

    ordered = rank_with_graph(eis, equal)
    assert ordered[0].event_id == ev_b.id   # low-hype first
    assert ordered[1].event_id == ev_a.id   # high-hype demoted despite equal graph signal


def test_graph_signal_never_crosses_priority_classes(session):
    # An archive item with a huge convergence signal must still rank below an immediate-priority
    # item with no signal — graph reorders WITHIN/by class, never overrides the class.
    ev_a, ev_b, ei_a, ei_b = _converging_vs_isolated(session)
    ei_a.priority_class = "archive"
    ei_b.priority_class = "immediate_priority"
    session.add(ei_a)
    session.add(ei_b)
    session.commit()
    g = _project_all(session)
    eis = session.exec(select(EnrichedItem)).all()
    signals = compute_signals(session, g, [e.event_id for e in eis], window_days=0)

    ordered = rank_with_graph(eis, signals)
    assert ordered[0].event_id == ev_b.id   # immediate_priority wins regardless of A's convergence
    assert ordered[1].event_id == ev_a.id


def test_isolated_event_has_zero_signal_outside_window(session):
    _converging_vs_isolated(session)
    g = _project_all(session)
    eis = session.exec(select(EnrichedItem)).all()
    # A 1-day window in the far future excludes the 2026-06-18 activity → no signal.
    from datetime import datetime, timezone
    future = datetime(2027, 1, 1, tzinfo=timezone.utc)
    signals = compute_signals(session, g, [e.event_id for e in eis], now=future, window_days=1)
    assert all(sig.score == 0.0 for sig in signals.values())
