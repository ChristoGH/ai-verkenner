"""Fetch-health surfacing — task 011 defect 2 (raised by D-017).

Offline and deterministic: injected fetchers, an in-memory SQLite DB, no network.

The invariant under test is a pair, and both halves matter:

1. A failing source must never abort a run (`CLAUDE.md` fail-safe isolation) — pinned here as a
   regression test because Defect 2's changes touch that exact code path.
2. A source that never yields must not be *invisible*. Isolation without surfacing means the
   registry keeps claiming coverage the corpus does not have, which is the silent correctness
   failure D-017 found: eight enabled sources, 0 rows, no signal anywhere.
"""

from __future__ import annotations

import pytest
from app.ingestion.health import (
    STATE_NO_ITEMS,
    STATE_NO_TOKEN,
    STATE_OK,
    STATE_STALE_WINDOW,
    attribute_new_counts,
    format_health_report,
    health_note,
    health_state,
    zero_yield_warnings,
)
from app.ingestion.orchestrator import run_ingestion
from app.models import SourceHealth
from app.schemas.raw_item import RawItem
from app.schemas.source import Source, SourceType
from app.storage.repository import upsert_source_health
from sqlmodel import select


def _source(name: str, source_type: SourceType = SourceType.rss, **kwargs) -> Source:
    base = dict(
        name=name,
        source_type=source_type,
        url="https://example.com/feed.xml",
        enabled=True,
        trust_level="high",
    )
    base.update(kwargs)
    return Source(**base)


def _item(source: Source, title: str) -> RawItem:
    return RawItem(
        source_name=source.name,
        source_type=source.source_type,
        title=title,
        url=f"https://example.com/{title}",
        summary=None,
    )


def _run_once(sources, fetchers, session, *, new_names=()):
    """One ingestion + health record, without the embed/dedup/enrich path."""
    run = run_ingestion(sources, fetchers, max_age_days=0, max_items=0)
    attribute_new_counts(run.results, new_names)
    upsert_source_health(session, run.results)
    return run


# ---- the four tests named in tasks/011-source-scope-and-fetch-health.md ----


def test_zero_yield_source_is_flagged_not_fatal(session):
    """Three consecutive empty runs flag the source loudly — and never abort the run."""
    quiet = _source("Quiet Feed")
    loud = _source("Working Feed")
    fetchers = {SourceType.rss: lambda s: [] if s.name == "Quiet Feed" else [_item(s, "a")]}

    for _ in range(3):
        run = _run_once([quiet, loud], fetchers, session)
        # The run itself is untouched by the health machinery: nothing raised, nothing dropped.
        assert run.failed == []
        assert len(run.items) == 1

    rows = session.exec(select(SourceHealth)).all()
    by_name = {r.source_name: r for r in rows}
    assert by_name["Quiet Feed"].consecutive_zero_yield == 3
    assert by_name["Working Feed"].consecutive_zero_yield == 0

    warnings = zero_yield_warnings(rows, zero_yield_warn=3)
    assert len(warnings) == 1
    assert "Quiet Feed" in warnings[0]
    assert "Working Feed" not in warnings[0]

    # Below the threshold nothing is reported — the warning is a streak, not a single bad run.
    assert zero_yield_warnings(rows, zero_yield_warn=4) == []


def test_zero_yield_streak_resets_on_a_yielding_run(session):
    """The streak counts CONSECUTIVE misses; one good run clears it."""
    src = _source("Intermittent")
    empty = {SourceType.rss: lambda s: []}
    full = {SourceType.rss: lambda s: [_item(s, "a")]}

    _run_once([src], empty, session)
    _run_once([src], empty, session)
    row = session.exec(select(SourceHealth)).first()
    assert row.consecutive_zero_yield == 2
    assert row.last_yield_at is None

    _run_once([src], full, session)
    session.refresh(row)
    assert row.consecutive_zero_yield == 0
    assert row.last_yield_at is not None


def test_fetch_error_isolated_run_continues(session):
    """Pins the existing invariant: one bad source never aborts a run (CLAUDE.md)."""
    boom = _source("Broken Feed")
    fine = _source("Working Feed")

    def fetcher(s):
        if s.name == "Broken Feed":
            raise RuntimeError("connection reset")
        return [_item(s, "a"), _item(s, "b")]

    run = _run_once([boom, fine], {SourceType.rss: fetcher}, session)

    # The run completed and kept the good source's items.
    assert len(run.items) == 2
    assert [r.source_name for r in run.failed] == ["Broken Feed"]
    assert [r.source_name for r in run.succeeded] == ["Working Feed"]

    # ...and the failure is now recorded rather than only logged.
    row = session.exec(
        select(SourceHealth).where(SourceHealth.source_name == "Broken Feed")
    ).first()
    assert "connection reset" in row.last_error
    assert row.last_ok_at is None
    assert row.consecutive_zero_yield == 1


def test_health_lists_all_enabled_sources(session):
    """Every enabled source appears — including one that has never run at all."""
    ran = _source("Has Run")
    never = _source("Never Run")
    _run_once([ran], {SourceType.rss: lambda s: [_item(s, "a")]}, session, new_names=["Has Run"])

    rows_by_name = {r.source_name: r for r in session.exec(select(SourceHealth)).all()}
    report = format_health_report(
        [ran.name, never.name], rows_by_name, zero_yield_warn=3
    )

    assert "Has Run" in report
    # The source with no health row at all must NOT be silently omitted — omitting it would
    # recreate the exact invisibility this task exists to remove.
    assert "Never Run" in report
    assert "never-run" in report
    assert "2 enabled source(s)" in report


def test_github_sources_report_missing_token_distinctly(session, monkeypatch):
    """A missing token reads as 'needs GITHUB_TOKEN', never as a broken feed."""
    from app.core import config

    monkeypatch.setattr(config.settings, "github_token", None)
    gated = _source(
        "Star velocity under topic:llm",
        SourceType.github_star_velocity,
        url="https://github.com/topics/llm",
        github_topic="llm",
    )
    dead = _source("Dead Feed")  # a real 0-entry feed, for contrast

    fetchers = {SourceType.github_star_velocity: lambda s: [], SourceType.rss: lambda s: []}
    for _ in range(3):
        _run_once([gated, dead], fetchers, session)

    rows = {r.source_name: r for r in session.exec(select(SourceHealth)).all()}
    gated_row = rows["Star velocity under topic:llm"]
    dead_row = rows["Dead Feed"]

    assert gated_row.needs_token is True
    assert dead_row.needs_token is False
    # Same zero yield, materially different diagnosis.
    assert health_state(gated_row) == STATE_NO_TOKEN
    assert health_state(dead_row) == STATE_NO_ITEMS
    assert "GITHUB_TOKEN" in health_note(gated_row)
    assert "not broken" in health_note(gated_row)
    assert "GITHUB_TOKEN" not in health_note(dead_row)
    assert "check the URL" in health_note(dead_row)

    # Both are still flagged — a token-gated source is surfaced, just with the right reason.
    warnings = zero_yield_warnings(rows.values(), zero_yield_warn=3)
    assert len(warnings) == 2
    token_line = next(w for w in warnings if "Star velocity" in w)
    assert "GITHUB_TOKEN" in token_line

    # With a token present, the source is no longer token-gated.
    monkeypatch.setattr(config.settings, "github_token", "x")
    _run_once([gated], fetchers, session)
    session.refresh(gated_row)
    assert gated_row.needs_token is False
    assert health_state(gated_row) == STATE_NO_ITEMS


# ---- the distinction the whole defect turns on ----


def test_healthy_but_low_cadence_source_is_not_reported_as_broken(session):
    """`stale-window` != `no-items`.

    This is the finding that corrects D-017's own diagnosis: of the eight "zero-yield" sources,
    several (LlamaIndex Releases, Eugene Yan) fetch perfectly and are merely quieter than
    SOURCE_MAX_AGE_DAYS. Reporting those as broken would send the human to fix a working URL.
    """
    src = _source("Low Cadence Blog")
    # Everything the fetcher returns is dropped by the recency cap.
    old = RawItem(
        source_name=src.name,
        source_type=SourceType.rss,
        title="an old post",
        url="https://example.com/old",
        published_at=None,
    )
    run = run_ingestion([src], {SourceType.rss: lambda s: [old]}, max_age_days=0, max_items=0)
    # Simulate the cap having dropped it: fetched 12, kept 0.
    run.results[0].fetched_count = 12
    run.results[0].item_count = 0
    upsert_source_health(session, run.results)

    row = session.exec(select(SourceHealth)).first()
    assert health_state(row) == STATE_STALE_WINDOW
    assert "healthy fetch" in health_note(row)
    assert "SOURCE_MAX_AGE_DAYS" in health_note(row)
    assert row.last_skipped_count == 12


def test_counts_separate_fetched_kept_new_and_skipped(session):
    """fetched / kept / new / skipped are recorded distinctly, per the task's Scope."""
    src = _source("Feed A")
    items = [_item(src, "a"), _item(src, "b"), _item(src, "c")]
    run = run_ingestion([src], {SourceType.rss: lambda s: items}, max_age_days=0, max_items=0)
    # Only one of the three was actually new to SQLite; the other two were already stored.
    attribute_new_counts(run.results, ["Feed A"])
    upsert_source_health(session, run.results)

    row = session.exec(select(SourceHealth)).first()
    assert row.last_fetched_count == 3
    assert row.last_item_count == 3
    assert row.last_new_count == 1
    assert row.last_skipped_count == 2   # fetched 3, stored 1
    assert health_state(row) == STATE_OK


@pytest.mark.parametrize("threshold", [1, 3, 5])
def test_zero_yield_warning_threshold_is_configurable(session, threshold):
    """SOURCE_ZERO_YIELD_WARN drives the flag; the default lives in config, not here."""
    src = _source("Quiet")
    for _ in range(threshold):
        _run_once([src], {SourceType.rss: lambda s: []}, session)
    rows = session.exec(select(SourceHealth)).all()
    assert len(zero_yield_warnings(rows, zero_yield_warn=threshold)) == 1
    assert zero_yield_warnings(rows, zero_yield_warn=threshold + 1) == []
