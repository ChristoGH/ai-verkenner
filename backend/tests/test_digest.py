"""GraphRAG digest (M7) — sections, weak-signal quadrant, honest noise count, SQLite-only degrade.

Offline + deterministic: in-memory SQLite, an InMemoryGraph for the Neo4j-expand, a fake LLM
provider (no network). Asserts tasks/008: all ten sections present; weak-signals draws only from the
horizon/archive quadrant; the noise count equals the archived/high-hype items; and the digest still
generates with no graph store (SQLite-only).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.api import dashboard_service
from app.api.deps import session_dep
from app.digests import generate_digest
from app.digests.sections import SECTION_HEADINGS, build_items, build_sections
from app.graph import InMemoryGraph, project_new_events
from app.main import app
from app.models import EnrichedItem, RawItem
from tests import graph_helpers as gh

TS = datetime(2026, 6, 18, tzinfo=timezone.utc)


class FakeProvider:
    """Deterministic, offline LLM provider — returns a fixed markdown digest."""

    name = "fake"

    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, *, system: str, user: str) -> str:
        return self._text


def _typed_item(session, source, event, *, title, url, source_type):
    item = RawItem(
        source_id=source.id, source_name=source.name, source_type=source_type,
        title=title, url=url, summary=title, dedup_key=url, content_hash="h:" + url,
        event_id=event.id, published_at=TS,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    if event.representative_item_id is None:
        event.representative_item_id = item.id
        session.add(event)
        session.commit()
    return item


def _seed(session):
    """A realistic mix: 1 must-know advisory, 1 should-read release, 2 converging weak signals
    (one from arXiv → research radar), 1 archive + 1 high-hype = 2 noise items.
    """
    s1, s2, s3 = (gh.add_source(session, f"src{i}") for i in (1, 2, 3))
    rag = gh.add_entity(session, "RAG", "concept")

    # Two converging horizon developments on RAG, from two distinct sources (genuine weak signal).
    # Dev 0 comes from an arXiv-typed item so it also lands in the research radar.
    weak = []
    for i, (src, stype) in enumerate(((s1, "arxiv"), (s2, "rss"))):
        ev = gh.add_event(session, f"RAG development {i}")
        item = _typed_item(session, src, ev, title=f"New RAG approach {i}",
                           url=f"https://{src.name}/rag{i}", source_type=stype)
        partner = gh.add_entity(session, f"RagPartner{i}", "tool")
        gh.add_relationship(session, rag, "advances", partner, event=ev, item=item)
        gh.add_enriched(session, ev, item, priority_class="horizon_signal", tags=["rag"],
                        relevance=1, novelty=3, actionability=2, strategic_potential=4, hype=1)
        weak.append(ev)

    # Must-know: a security advisory (relevance 5) from a github_advisories source → also a risk.
    ev_adv = gh.add_event(session, "Critical advisory in langchain")
    item_adv = _typed_item(session, s3, ev_adv, title="CVE in langchain",
                           url="https://src3/adv", source_type="github_advisories")
    gh.add_enriched(session, ev_adv, item_adv, priority_class="immediate_priority",
                    tags=["security"], relevance=5, novelty=3, actionability=4,
                    strategic_potential=2, hype=0)
    adv_row = session.exec(
        select(EnrichedItem).where(EnrichedItem.event_id == ev_adv.id)
    ).one()
    adv_row.recommended_action = "Pin langchain and patch this week."
    session.add(adv_row)
    session.commit()

    # Should-read: an operational release (github_releases) → also a tool change.
    ev_rel = gh.add_event(session, "FastAPI 1.2 released")
    item_rel = _typed_item(session, s3, ev_rel, title="FastAPI 1.2",
                           url="https://src3/rel", source_type="github_releases")
    gh.add_enriched(session, ev_rel, item_rel, priority_class="operational_update",
                    tags=["release"], relevance=3, novelty=3, actionability=3,
                    strategic_potential=2, hype=1)

    # Noise 1: an archive item (singleton, no convergence).
    ev_arc = gh.add_event(session, "Archived chatter")
    item_arc = _typed_item(session, s3, ev_arc, title="Old news", url="https://src3/arc",
                           source_type="rss")
    lone = gh.add_entity(session, "LoneThing", "concept")
    other = gh.add_entity(session, "OtherThing", "concept")
    gh.add_relationship(session, lone, "relates_to", other, event=ev_arc, item=item_arc)
    gh.add_enriched(session, ev_arc, item_arc, priority_class="archive", tags=["misc"],
                    relevance=1, novelty=1, actionability=1, strategic_potential=1, hype=2)

    # Noise 2: a high-hype operational update (hype 5 → demoted as noise).
    ev_hype = gh.add_event(session, "Loud marketing splash")
    item_hype = _typed_item(session, s3, ev_hype, title="Revolutionary!!!", url="https://src3/hype",
                            source_type="rss")
    gh.add_enriched(session, ev_hype, item_hype, priority_class="operational_update",
                    tags=["marketing"], relevance=3, novelty=2, actionability=1,
                    strategic_potential=1, hype=5)

    return {"weak": weak, "advisory": ev_adv, "release": ev_rel,
            "archive": ev_arc, "hype": ev_hype}


def _store_with_seed(session):
    seeded = _seed(session)
    store = InMemoryGraph()
    project_new_events(session, store, session.exec(select(RawItem)).all())
    return store, seeded


def _data(session, store):
    rows = dashboard_service.load_enriched(session)
    signals = dashboard_service.compute_signals(session, store, rows)
    items = build_items(session, rows, signals)
    return build_sections(items, signals, high_hype=4, section_limit=8, graphrag=store is not None,
                          period_start=None, period_end=None)


# ---- structured sections ----


def test_noise_count_is_archived_plus_high_hype(session):
    store, _seeded = _store_with_seed(session)
    data = _data(session, store)
    # Exactly the archive item + the hype-5 item.
    assert data.noise_count == 2
    assert data.total_events == 6 and data.item_count == 4


def test_weak_signals_only_from_horizon_quadrant(session):
    store, seeded = _store_with_seed(session)
    data = _data(session, store)
    assert {it.priority_class for it in data.weak_signals} <= {"horizon_signal", "archive"}
    # The two converging RAG developments are the weak signals.
    assert {it.event_id for it in data.weak_signals} == {e.id for e in seeded["weak"]}
    assert all(it.graph_score > 0 for it in data.weak_signals)


def test_sections_route_by_source_fact(session):
    store, seeded = _store_with_seed(session)
    data = _data(session, store)
    assert {it.event_id for it in data.must_know} == {seeded["advisory"].id}
    assert {it.event_id for it in data.should_read} == {seeded["release"].id}
    assert seeded["advisory"].id in {it.event_id for it in data.risks}          # advisory → risk
    assert seeded["release"].id in {it.event_id for it in data.tool_changes}    # release → tool
    assert seeded["weak"][0].id in {it.event_id for it in data.research_radar}  # arXiv → research
    # Opportunities = high strategic, low hype (the RAG weak signals), never the noise.
    assert {it.event_id for it in data.opportunities} == {e.id for e in seeded["weak"]}


# ---- generation (fallback + LLM + degrade) ----


def test_fallback_digest_has_all_ten_sections(session):
    store, _seeded = _store_with_seed(session)
    digest = generate_digest(session, provider=None, graph_store=store, period_days=0)
    assert digest.method == "fallback"
    for heading in SECTION_HEADINGS:
        assert f"## {heading}" in digest.content_md
    # Honest noise count surfaced in the body.
    assert "2 item(s) were archived or high-hype" in digest.content_md
    assert digest.noise_count == 2


def test_digest_preserves_source_links(session):
    store, _seeded = _store_with_seed(session)
    digest = generate_digest(session, provider=None, graph_store=store, period_days=0)
    assert "https://src3/adv" in digest.content_md  # the advisory's source link is preserved


def test_llm_provider_composes_when_present(session):
    store, _seeded = _store_with_seed(session)
    fake = FakeProvider("# Composed digest\n\nDecisions, not links.\n")
    digest = generate_digest(session, provider=fake, graph_store=store, period_days=0)
    assert digest.method == "llm"
    assert digest.content_md.startswith("# Composed digest")


def test_graphrag_degrades_to_sqlite_only(session):
    _store, _seeded = _store_with_seed(session)
    # No graph store, no qdrant client, no embedder → SQLite-only selection.
    digest = generate_digest(
        session, provider=None, graph_store=None, qdrant_client=None, embedder=None, period_days=0,
    )
    assert digest.graphrag is False
    assert digest.noise_count == 2
    for heading in SECTION_HEADINGS:
        assert f"## {heading}" in digest.content_md
    # The weak-signal quadrant is still present even without convergence ranking.
    assert "Weak signals" in digest.content_md


# ---- read API ----


@pytest.fixture
def client_with_digest(session):
    store, _seeded = _store_with_seed(session)
    digest = generate_digest(session, provider=None, graph_store=store, period_days=0)
    app.dependency_overrides[session_dep] = lambda: session
    try:
        yield TestClient(app), digest
    finally:
        app.dependency_overrides.clear()


def test_get_digests_lists_newest_first(client_with_digest):
    tc, digest = client_with_digest
    body = tc.get("/digests").json()
    assert len(body) == 1
    assert body[0]["id"] == digest.id
    assert body[0]["noise_count"] == 2 and body[0]["method"] == "fallback"


def test_get_digest_detail_returns_content(client_with_digest):
    tc, digest = client_with_digest
    body = tc.get(f"/digests/{digest.id}").json()
    assert body["content_md"].startswith("# Weekly digest")
    assert len(body["event_ids"]) > 0


def test_get_missing_digest_is_404(client_with_digest):
    tc, _digest = client_with_digest
    assert tc.get("/digests/9999").status_code == 404
