"""Tests for M4 enrichment + extraction.

Deterministic and offline: a fake LLM provider, in-memory SQLite, no network or API key.
"""

from __future__ import annotations

import json

import pytest
from sqlmodel import Session, select

from app.enrichment import Enricher, enricher as enricher_mod
from app.enrichment.enricher import enrich_new_events
from app.models import EnrichedItem, Entity, Event, RawItem, Relationship
from app.scoring.priority import compute_priority_class


class FakeProvider:
    """A deterministic provider: returns canned JSON per template.

    Dispatch checks 'Extract Graph' BEFORE 'Weak Signal' because the extract-graph template
    mentions "Weak Signal of the Week".
    """

    name = "fake"

    def __init__(
        self,
        *,
        scores=None,
        category="research",
        tags=None,
        summary="The source states a fact.",
        why="Interpretation of why it matters.",
        connection="Interpretation of the connection.",
        action="Interpretation of the action.",
        weak=None,
        entities=None,
        relationships=None,
        bad_template=None,
    ):
        self.scores = scores or {
            "relevance": 3, "novelty": 3, "actionability": 2,
            "strategic_potential": 3, "hype": 2,
        }
        self.category = category
        self.tags = tags if tags is not None else ["llm"]
        self.summary = summary
        self.why = why
        self.connection = connection
        self.action = action
        self.weak = weak or {"is_weak_signal": False}
        self.entities = entities or []
        self.relationships = relationships or []
        self.bad_template = bad_template  # a marker string; that template returns garbage

    def complete(self, *, system: str, user: str) -> str:
        if self.bad_template and self.bad_template in system:
            return "Sorry, I cannot produce JSON for this one."
        if "Classify Item" in system:
            return json.dumps(
                {"category": self.category, "tags": self.tags, "scores": self.scores}
            )
        if "Summarise Item" in system:
            return json.dumps({
                "source_url": "echoed",
                "summary": self.summary,
                "why_it_matters": self.why,
                "connection_to_user_work": self.connection,
                "recommended_action": self.action,
            })
        if "Extract Graph" in system:
            return json.dumps({"entities": self.entities, "relationships": self.relationships})
        if "Weak Signal" in system:
            return json.dumps(self.weak)
        return "{}"


def _event_with_item(session: Session, *, title="An item", summary="Source fact.",
                     url="https://a.example/1", source_type="rss", published=None) -> Event:
    item = RawItem(
        source_name="Feed A", source_type=source_type, title=title, url=url,
        summary=summary, dedup_key=url, content_hash="h-" + url, published_at=published,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    event = Event(title=title, representative_item_id=item.id)
    session.add(event)
    session.commit()
    session.refresh(event)
    item.event_id = event.id
    session.add(item)
    session.commit()
    return event


# ---- Output parsing → EnrichedItem ----


def test_llm_output_maps_to_enriched_item(session):
    provider = FakeProvider(
        scores={"relevance": 4, "novelty": 5, "actionability": 3,
                "strategic_potential": 4, "hype": 1},
        category="model_release", tags=["llm", "openai"],
    )
    event = _event_with_item(session, url="https://a.example/x")
    enriched = Enricher(provider).enrich_event(session, event)

    assert enriched.method == "llm"
    assert enriched.category == "model_release"
    assert enriched.tags == ["llm", "openai"]
    assert (enriched.relevance, enriched.novelty, enriched.actionability,
            enriched.strategic_potential, enriched.hype) == (4, 5, 3, 4, 1)
    assert enriched.source_url == "https://a.example/x"  # preserved


def test_fact_and_interpretation_are_separate_fields(session):
    provider = FakeProvider(
        summary="OpenAI released GPT-5.",
        why="This could matter for tooling.",
        connection="Relates to the user's LLM stack.",
        action="Evaluate it this week.",
    )
    event = _event_with_item(session)
    e = Enricher(provider).enrich_event(session, event)

    assert e.summary == "OpenAI released GPT-5."          # source fact only
    assert e.why_it_matters == "This could matter for tooling."  # interpretation, separate
    assert e.connection_to_user_work == "Relates to the user's LLM stack."
    assert e.recommended_action == "Evaluate it this week."
    # The fact field must not have absorbed the interpretation.
    assert "could matter" not in e.summary


# ---- Priority class comes from the canonical rule ----


@pytest.mark.parametrize(
    "relevance, strategic_potential",
    [(5, 0), (4, 3), (4, 2), (3, 5), (2, 4), (1, 1), (0, 0)],
)
def test_priority_class_matches_canonical_rule(session, relevance, strategic_potential):
    provider = FakeProvider(scores={
        "relevance": relevance, "novelty": 2, "actionability": 2,
        "strategic_potential": strategic_potential, "hype": 2,
    })
    event = _event_with_item(session, url=f"https://a.example/{relevance}-{strategic_potential}")
    e = Enricher(provider).enrich_event(session, event)
    assert e.priority_class == compute_priority_class(relevance, strategic_potential)


def test_priority_class_uses_imported_canonical_function(session, monkeypatch):
    # Prove the enricher calls compute_priority_class (the single source of truth), not a copy.
    calls = []
    real = enricher_mod.compute_priority_class

    def spy(relevance, strategic_potential):
        calls.append((relevance, strategic_potential))
        return real(relevance, strategic_potential)

    monkeypatch.setattr(enricher_mod, "compute_priority_class", spy)
    provider = FakeProvider(scores={"relevance": 5, "novelty": 1, "actionability": 1,
                                    "strategic_potential": 0, "hype": 2})
    event = _event_with_item(session)
    Enricher(provider).enrich_event(session, event)
    assert calls == [(5, 0)]


# ---- Degrade paths ----


def test_malformed_llm_output_degrades_to_fallback_without_raising(session):
    # Classifier returns garbage → the whole event falls back, no exception.
    provider = FakeProvider(bad_template="Classify Item")
    event = _event_with_item(session, summary="A plain item.")
    e = Enricher(provider).enrich_event(session, event)  # must not raise
    assert e.method == "fallback"
    assert e.priority_class == compute_priority_class(e.relevance, e.strategic_potential)
    assert e.summary  # fallback still produced a fact-only summary


def test_no_provider_uses_rule_based_fallback(session):
    event = _event_with_item(session, summary="OpenAI ships a thing.", source_type="github_releases")
    e = Enricher(None).enrich_event(session, event)
    assert e.method == "fallback"
    # Fallback summary is the source's own text (fact, not inference).
    assert e.summary == "OpenAI ships a thing."
    assert 0 <= e.hype <= 5
    assert e.priority_class in {
        "immediate_priority", "operational_update", "horizon_signal", "archive"
    }


# ---- Entity resolution (exact + normalised) ----


def test_entity_normalisation_merges_variants(session):
    provider = FakeProvider(
        entities=[
            {"name": "OpenAI", "type": "org"},
            {"name": "openai ", "type": "org"},   # same entity, different surface form
            {"name": "GPT-5", "type": "model"},
        ],
        relationships=[{"subject": "OpenAI", "predicate": "released", "object": "GPT-5"}],
    )
    event = _event_with_item(session)
    Enricher(provider).enrich_event(session, event)

    orgs = session.exec(select(Entity).where(Entity.type == "org")).all()
    assert len(orgs) == 1  # "OpenAI" and "openai " resolved to one row
    assert orgs[0].normalised_name == "openai"
    rels = session.exec(select(Relationship)).all()
    assert len(rels) == 1


def test_relationships_are_timestamped_from_item(session):
    from datetime import datetime, timezone
    ts = datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc)
    provider = FakeProvider(
        entities=[{"name": "Qdrant", "type": "tool"}, {"name": "RAG", "type": "concept"}],
        relationships=[{"subject": "Qdrant", "predicate": "supports", "object": "RAG"}],
    )
    event = _event_with_item(session, published=ts)
    Enricher(provider).enrich_event(session, event)
    rel = session.exec(select(Relationship)).first()
    # SQLite stores naive datetimes; compare the wall-clock value (UTC) it round-trips.
    assert rel.ts is not None
    assert rel.ts.replace(tzinfo=None) == ts.replace(tzinfo=None)


def test_entities_capped_per_item(session):
    many = [{"name": f"Tool{i}", "type": "tool"} for i in range(20)]
    provider = FakeProvider(entities=many)
    event = _event_with_item(session)
    Enricher(provider, max_entities=5).enrich_event(session, event)
    assert len(session.exec(select(Entity)).all()) == 5


# ---- Idempotency (enrich only new events, once) ----


def test_enrich_new_events_is_idempotent(session):
    provider = FakeProvider()
    event = _event_with_item(session)
    rows = session.exec(select(RawItem).where(RawItem.event_id == event.id)).all()
    enricher = Enricher(provider)

    first = enrich_new_events(session, enricher, rows)
    second = enrich_new_events(session, enricher, rows)  # same rows again
    assert first == 1
    assert second == 0
    assert len(session.exec(select(EnrichedItem)).all()) == 1


def test_enrich_new_events_skips_already_enriched_event(session):
    provider = FakeProvider()
    event = _event_with_item(session)
    # Enrich once directly.
    Enricher(provider).enrich_event(session, event)
    # A near-dup later joins the same (already-enriched) event; it must not re-enrich.
    dup = RawItem(source_name="Feed B", source_type="rss", title="dup",
                  url="https://b.example/1", summary="x", dedup_key="https://b.example/1",
                  content_hash="h2", event_id=event.id)
    session.add(dup)
    session.commit()
    session.refresh(dup)
    enriched = enrich_new_events(session, Enricher(provider), [dup])
    assert enriched == 0
    assert len(session.exec(select(EnrichedItem)).all()) == 1
