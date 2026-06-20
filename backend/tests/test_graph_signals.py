"""Tests for graph-aware ranking with hub-dampening (M5.5).

Offline: in-memory graph + SQLite. The headline checks come straight from the M6 smoke findings:
a *ubiquitous hub* must rank below a *rare entity converging across independent sources*, a
*single-source prolific* entity must not dominate, a *singleton* (one development) scores ~0, and
the `why` evidence equals the driving entity's distinct sources. The priority-class and hype
invariants from M5 still hold.
"""

from __future__ import annotations

from sqlmodel import select

from app.graph import InMemoryGraph, project_new_events
from app.models import EnrichedItem, RawItem
from app.scoring.graph_signals import GraphSignal, compute_signals
from app.scoring.ranking import rank_with_graph
from tests import graph_helpers as gh


def _project_all(session):
    g = InMemoryGraph()
    project_new_events(session, g, session.exec(select(RawItem)).all())
    return g


def _event_mentioning(session, title, source, entity, *, pclass="archive", hype=1):
    """One development from `source` whose item mentions `entity` (+ a unique throwaway partner)."""
    ev = gh.add_event(session, title)
    item = gh.add_item(session, source, ev, title=title, url=f"https://{source.name}/{title}")
    partner = gh.add_entity(session, f"partner::{title}", "concept")  # unique → singleton, never a driver
    gh.add_relationship(session, entity, "rel", partner, event=ev, item=item)
    gh.add_enriched(session, ev, item, priority_class=pclass, hype=hype)
    return ev


def _signals(session, **kw):
    g = _project_all(session)
    eis = session.exec(select(EnrichedItem)).all()
    # recency_weight=0 isolates the convergence dampening so suppressed entities score exactly 0.
    return eis, compute_signals(session, g, [e.event_id for e in eis], window_days=0,
                                recency_weight=0.0, **kw)


def test_rare_cross_source_entity_outranks_ubiquitous_hub(session):
    s1, s2, s3 = (gh.add_source(session, n) for n in ("S1", "S2", "S3"))
    github = gh.add_entity(session, "GitHub", "org")     # the hub: everywhere, many sources
    rag = gh.add_entity(session, "RAG", "concept")        # rare: 2 developments, 2 sources

    hub_events = [_event_mentioning(session, f"hub{i}", (s1, s2, s3)[i % 3], github)
                  for i in range(6)]
    rare_events = [_event_mentioning(session, f"rare{i}", src, rag)
                   for i, src in enumerate((s1, s2))]

    eis, signals = _signals(session)
    rare_sig = signals[rare_events[0].id]
    hub_sig = signals[hub_events[0].id]

    # Both are "convergent" by raw sources, but IDF + breadth flip the ranking.
    assert rare_sig.driver == "RAG" and rare_sig.convergence == 2 and rare_sig.event_count == 2
    assert hub_sig.driver == "GitHub" and hub_sig.convergence == 3 and hub_sig.event_count == 6
    assert rare_sig.idf > hub_sig.idf                 # rare entity is rarer → higher IDF
    assert rare_sig.score > hub_sig.score             # …so it outranks the hub
    # The whole feed: a rare-RAG development sits at the top, ahead of every hub development.
    ordered = rank_with_graph(eis, signals)
    assert ordered[0].event_id in {e.id for e in rare_events}


def test_single_source_prolific_entity_does_not_dominate(session):
    blog = gh.add_source(session, "BlogA")
    s1, s2 = gh.add_source(session, "S1"), gh.add_source(session, "S2")
    author = gh.add_entity(session, "Prolific Author", "person")  # 4 developments, ALL one feed
    rag = gh.add_entity(session, "RAG", "concept")                # 2 developments, 2 feeds

    author_events = [_event_mentioning(session, f"auth{i}", blog, author) for i in range(4)]
    rare_events = [_event_mentioning(session, f"rare{i}", src, rag)
                   for i, src in enumerate((s1, s2))]

    eis, signals = _signals(session)
    # A single prolific feed is NOT convergence — the author's events carry no signal.
    for ev in author_events:
        assert signals[ev.id].score == 0.0
        assert signals[ev.id].convergence == 0
        assert "convergence" not in signals[ev.id].why
    # The genuinely cross-source RAG development wins.
    ordered = rank_with_graph(eis, signals)
    assert ordered[0].event_id in {e.id for e in rare_events}


def test_singleton_development_scores_zero_even_with_two_sources(session):
    s1, s2 = gh.add_source(session, "S1"), gh.add_source(session, "S2")
    oneoff = gh.add_entity(session, "OneOff", "concept")
    other = gh.add_entity(session, "Other", "concept")

    # ONE development covered by two sources → distinct_sources=2 but event_count=1 → suppressed.
    ev = gh.add_event(session, "single development")
    it1 = gh.add_item(session, s1, ev, title="cover A", url="https://S1/x")
    gh.add_item(session, s2, ev, title="cover B", url="https://S2/x")
    gh.add_relationship(session, oneoff, "rel", other, event=ev, item=it1)
    gh.add_enriched(session, ev, it1, priority_class="archive", hype=1)

    eis, signals = _signals(session)
    sig = signals[ev.id]
    assert sig.score == 0.0          # not an emerging *cross-development* cluster
    assert sig.convergence == 0
    assert sig.why == ""


def test_why_evidence_equals_driving_entity_sources(session):
    s1, s2, s3 = (gh.add_source(session, n) for n in ("S1", "S2", "S3"))
    rag = gh.add_entity(session, "RAG", "concept")
    github = gh.add_entity(session, "GitHub", "org")
    # RAG across S1+S2 (2 developments); GitHub everywhere (so RAG wins as driver on its events).
    rare_events = [_event_mentioning(session, f"rare{i}", src, rag)
                   for i, src in enumerate((s1, s2))]
    for i in range(4):
        _event_mentioning(session, f"hub{i}", (s1, s2, s3)[i % 3], github)

    _eis, signals = _signals(session)
    sig = signals[rare_events[0].id]
    assert sig.driver == "RAG"
    # The evidence behind the `why` IS the driving entity's distinct sources (M6 finding #3).
    assert set(sig.evidence_sources) == {"S1", "S2"}
    assert f"across {sig.convergence} independent sources" in sig.why


def test_hype_still_demotes_when_graph_signal_is_equal(session):
    # Two archive items with an identical (forced) graph signal — hype must still demote the noisy one.
    s1 = gh.add_source(session, "S1")
    e1 = gh.add_entity(session, "X", "concept")
    ev_noisy = _event_mentioning(session, "noisy", s1, e1, hype=5)
    ev_clean = _event_mentioning(session, "clean", s1, e1, hype=0)
    eis = session.exec(select(EnrichedItem)).all()
    equal = {e.event_id: GraphSignal(convergence=2, score=2.0, why="x") for e in eis}

    ordered = rank_with_graph(eis, equal)
    by_id = {e.event_id: e for e in eis}
    assert by_id[ordered[0].event_id].event_id != by_id[ordered[-1].event_id].event_id
    # The low-hype item ranks ahead of the high-hype one.
    noisy_pos = next(i for i, e in enumerate(ordered) if e.event_id == ev_noisy.id)
    clean_pos = next(i for i, e in enumerate(ordered) if e.event_id == ev_clean.id)
    assert clean_pos < noisy_pos


def test_graph_signal_never_crosses_priority_classes(session):
    # An archive item with a huge signal must still rank below an immediate-priority item with none.
    s1 = gh.add_source(session, "S1")
    e1 = gh.add_entity(session, "X", "concept")
    ev_archive = _event_mentioning(session, "archive-strong", s1, e1, pclass="archive")
    ev_immediate = _event_mentioning(session, "immediate-none", s1, e1, pclass="immediate_priority")
    eis = session.exec(select(EnrichedItem)).all()
    forced = {
        ev_archive.id: GraphSignal(score=99.0),
        ev_immediate.id: GraphSignal(score=0.0),
    }
    ordered = rank_with_graph(eis, forced)
    assert ordered[0].event_id == ev_immediate.id
    assert ordered[1].event_id == ev_archive.id


def test_no_signal_outside_window(session):
    s1, s2 = gh.add_source(session, "S1"), gh.add_source(session, "S2")
    rag = gh.add_entity(session, "RAG", "concept")
    _event_mentioning(session, "rare0", s1, rag)
    _event_mentioning(session, "rare1", s2, rag)
    g = _project_all(session)
    eis = session.exec(select(EnrichedItem)).all()
    from datetime import datetime, timezone
    future = datetime(2027, 1, 1, tzinfo=timezone.utc)
    signals = compute_signals(session, g, [e.event_id for e in eis], now=future, window_days=1)
    assert all(sig.score == 0.0 for sig in signals.values())
