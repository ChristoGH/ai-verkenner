"""`app.cli enrich --backfill` — draining Events an interrupted run left unenriched.

`run` only enriches the Events *it* introduced, so an interrupted run strands everything it
persisted but never reached. These tests pin the backfill that recovers them.
"""

from __future__ import annotations

import contextlib

import pytest
from sqlmodel import select

from app import cli
from app.models import EnrichedItem, Event
from tests.test_enrichment import FakeProvider, _event_with_item


@pytest.fixture
def wired(session, monkeypatch):
    """Point the CLI at the in-memory test session and a deterministic provider."""
    @contextlib.contextmanager
    def _get_session():
        yield session

    monkeypatch.setattr(cli, "init_db", lambda: None)
    monkeypatch.setattr(cli, "get_session", _get_session)
    monkeypatch.setattr(cli, "get_provider", lambda: FakeProvider())
    return session


def test_backfill_enriches_only_the_unenriched_events(wired, capsys):
    session = wired
    a = _event_with_item(session, title="A", url="https://a.example/1")
    b = _event_with_item(session, title="B", url="https://b.example/1")
    # `a` is already enriched — the backfill must leave it alone and not re-bill it.
    cli.Enricher(FakeProvider()).enrich_event(session, a)
    before = session.exec(
        select(EnrichedItem).where(EnrichedItem.event_id == a.id)
    ).first()

    assert cli.main(["enrich", "--backfill"]) == 0

    rows = session.exec(select(EnrichedItem)).all()
    assert {r.event_id for r in rows} == {a.id, b.id}
    # `a` was not re-enriched (same row, not a replacement).
    assert session.exec(
        select(EnrichedItem).where(EnrichedItem.event_id == a.id)
    ).first().id == before.id
    assert "enriched=1" in capsys.readouterr().out


def test_backfill_dry_run_enriches_nothing(wired, capsys):
    _event_with_item(wired, title="A", url="https://a.example/1")

    assert cli.main(["enrich", "--backfill", "--dry-run"]) == 0

    assert wired.exec(select(EnrichedItem)).all() == []
    assert "would be enriched" in capsys.readouterr().out


def test_backfill_limit_caps_the_spend(wired, capsys):
    for i in range(3):
        _event_with_item(wired, title=f"E{i}", url=f"https://e{i}.example/1")

    assert cli.main(["enrich", "--backfill", "--limit", "2"]) == 0

    assert len(wired.exec(select(EnrichedItem)).all()) == 2
    assert "enriched=2" in capsys.readouterr().out


def test_backfill_isolates_a_failing_event(wired, capsys, monkeypatch):
    """One bad Event must not end the backfill — the CLAUDE.md fail-safe invariant."""
    _event_with_item(wired, title="A", url="https://a.example/1")
    _event_with_item(wired, title="B", url="https://b.example/1")

    calls = {"n": 0}
    real = cli.Enricher.enrich_event

    def flaky(self, session, event):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom: simulated enrichment failure")
        return real(self, session, event)

    monkeypatch.setattr(cli.Enricher, "enrich_event", flaky)

    assert cli.main(["enrich", "--backfill"]) == 0

    out = capsys.readouterr().out
    assert "enriched=1" in out and "skipped=1" in out
    assert len(wired.exec(select(Event)).all()) == 2
