"""Fetch-health surfacing (task 011 defect 2 / D-017) — make a silent source visible.

`CLAUDE.md` requires that one bad source never breaks a run, and the orchestrator honours that:
every fetch is isolated, every failure is caught, the run carries on. That invariant has a blind
side. A source that *never* yields is equally silent — no exception, no failure, nothing to see —
so the registry goes on claiming coverage the corpus does not have. In an early-warning system
that is a correctness failure, not a cosmetic one: D-017 found **eight enabled sources
contributing 0 rows to a 266-item corpus**, and none of them was visible anywhere.

This module is **reporting only**. It never retries, backs off, trips a breaker, or disables a
source. Surfacing is the whole job; the human decides what to do about it.

The distinction it exists to draw is between the several very different reasons a source shows
zero, which the raw "0 rows" conflates:

* **no-token** — a `github_*` source with no `GITHUB_TOKEN`. Skipped by design (ADR 0002:
  degrade, never crash). Nothing is wrong with it.
* **stale-window** — the fetch worked and returned items; none was recent enough to survive
  `SOURCE_MAX_AGE_DAYS`. The source is healthy and simply publishes less often than the window.
* **no-items** — the fetch "succeeded" (HTTP 200) but parsed to zero entries. This is the
  genuinely broken case: a dead feed, or a URL pointing at an HTML page rather than a feed.
* **error** — the fetch raised. Already isolated by the orchestrator; recorded here so it does
  not vanish into the log.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

from app.ingestion.orchestrator import SourceRunResult

# Health states, worst-news-first when ordering the report.
STATE_ERROR = "error"
STATE_NO_ITEMS = "no-items"
STATE_STALE_WINDOW = "stale-window"
STATE_NO_TOKEN = "no-token"
STATE_NEVER_RUN = "never-run"
STATE_OK = "ok"

_STATE_ORDER = {
    STATE_ERROR: 0,
    STATE_NO_ITEMS: 1,
    STATE_STALE_WINDOW: 2,
    STATE_NO_TOKEN: 3,
    STATE_NEVER_RUN: 4,
    STATE_OK: 5,
}


def attribute_new_counts(
    results: Sequence[SourceRunResult], source_names: Iterable[str]
) -> list[SourceRunResult]:
    """Fill each result's `new_count` from the source names of the rows actually persisted.

    `source_names` is one name per newly-stored RawItem (duplicates expected — that is the count).
    A source that fetched items but stored none gets 0, not None: "we stored nothing new from you"
    is a real observation, distinct from "we never asked".
    """
    counts = Counter(source_names)
    for result in results:
        if result.ok:
            result.new_count = counts.get(result.source_name, 0)
    return list(results)


def health_state(row) -> str:
    """Classify one `SourceHealth` row. See the module docstring for what each state means."""
    if row is None:
        return STATE_NEVER_RUN
    if row.last_error:
        return STATE_ERROR
    if row.last_item_count > 0:
        return STATE_OK
    if row.needs_token:
        return STATE_NO_TOKEN
    if row.last_fetched_count > 0:
        return STATE_STALE_WINDOW
    return STATE_NO_ITEMS


def health_note(row) -> str:
    """A one-line, actionable reason for this row's state — what a human would need to act."""
    state = health_state(row)
    if state == STATE_NEVER_RUN:
        return "no run recorded yet"
    if state == STATE_ERROR:
        return f"last fetch failed: {row.last_error}"
    if state == STATE_NO_TOKEN:
        return "needs GITHUB_TOKEN (skipped by design, not broken)"
    if state == STATE_STALE_WINDOW:
        return (
            f"healthy fetch: {row.last_fetched_count} item(s) returned, none within the recency "
            f"window — the source publishes less often than SOURCE_MAX_AGE_DAYS"
        )
    if state == STATE_NO_ITEMS:
        return "fetch returned 0 items — check the URL actually serves a feed"
    return ""


def _stamp(value) -> str:
    return value.date().isoformat() if value else "never"


def format_health_report(
    source_names: Sequence[str], rows_by_name: dict, *, zero_yield_warn: int
) -> str:
    """Render `sources --health`: one line per enabled source, worst news first.

    `source_names` is every ENABLED source in the registry — including ones with no health row at
    all, which are reported as `never-run` rather than omitted. Omitting them would reproduce the
    exact invisibility this task exists to remove.
    """
    header = (
        f"source health — {len(source_names)} enabled source(s); "
        f"zero-yield warning at {zero_yield_warn} consecutive run(s)\n"
    )
    if not source_names:
        return header + "  (no enabled sources in the registry)"

    ordered = sorted(
        source_names,
        key=lambda n: (_STATE_ORDER[health_state(rows_by_name.get(n))], n.lower()),
    )
    width = min(max((len(n) for n in source_names), default=20), 44)
    lines = [
        header,
        f"  {'STATE':<13} {'SOURCE':<{width}} {'LAST YIELD':<11} "
        f"{'FETCH':>6} {'KEPT':>5} {'NEW':>5} {'SKIP':>5} {'ZERO':>5}  NOTE",
    ]
    for name in ordered:
        row = rows_by_name.get(name)
        state = health_state(row)
        if row is None:
            lines.append(
                f"  {state:<13} {name[:width]:<{width}} {'never':<11} "
                f"{'-':>6} {'-':>5} {'-':>5} {'-':>5} {'-':>5}  {health_note(row)}"
            )
            continue
        lines.append(
            f"  {state:<13} {name[:width]:<{width}} {_stamp(row.last_yield_at):<11} "
            f"{row.last_fetched_count:>6} {row.last_item_count:>5} {row.last_new_count:>5} "
            f"{row.last_skipped_count:>5} {row.consecutive_zero_yield:>5}  {health_note(row)}"
        )
    return "\n".join(lines)


def zero_yield_warnings(rows: Iterable, *, zero_yield_warn: int) -> list[str]:
    """Loud, non-fatal lines for sources that have yielded nothing for N consecutive runs.

    Returns strings rather than printing or raising: the caller decides where they go, and NOTHING
    here can abort a run. A `no-token` source is reported with its own reason so a missing token
    never reads as a broken feed.
    """
    warnings: list[str] = []
    for row in sorted(rows, key=lambda r: (-r.consecutive_zero_yield, r.source_name.lower())):
        if row.consecutive_zero_yield < zero_yield_warn:
            continue
        warnings.append(
            f"  {row.source_name} — 0 items for {row.consecutive_zero_yield} consecutive run(s); "
            f"{health_note(row)}"
        )
    return warnings
