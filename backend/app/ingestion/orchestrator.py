"""Ingestion orchestrator — run the registry into in-memory RawItems, fail-safe per source.

The single invariant this module exists to guarantee: **one bad source never aborts the run.**
Each source is fetched in isolation; any exception is caught, logged, and recorded as a failed
`SourceRunResult`, and the run carries on. The result reports which sources succeeded and which
failed (with the reason), alongside the collected items.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.ingestion.fetchers import FETCHERS, Fetcher
from app.ingestion.fetchers.github_intelligence import needs_github_token
from app.schemas.raw_item import RawItem
from app.schemas.source import Source, SourceType

logger = logging.getLogger(__name__)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def apply_recency_cap(
    items: list[RawItem],
    *,
    max_age_days: int,
    max_items: int,
    now: datetime | None = None,
) -> list[RawItem]:
    """Bound one source's items by recency window + a hard ceiling (M6.5). Pure + fail-safe.

    `max_age_days > 0` drops items older than the window (undated items are kept — we can't judge
    their age, and the ceiling still bounds them). `max_items > 0` keeps only the newest N. This is
    what makes archive-serving feeds (e.g. Hugging Face's 803 entries) affordable in a full run.
    """
    now = now or datetime.now(timezone.utc)
    kept = items
    if max_age_days and max_age_days > 0:
        cutoff = now - timedelta(days=max_age_days)
        kept = [it for it in kept if (_as_utc(it.published_at) is None
                                      or _as_utc(it.published_at) >= cutoff)]
    if max_items and max_items > 0 and len(kept) > max_items:
        # Newest first; undated sink to the bottom so dated-recent items win the ceiling.
        kept = sorted(
            kept,
            key=lambda it: (_as_utc(it.published_at) is not None,
                            _as_utc(it.published_at) or datetime.min.replace(tzinfo=timezone.utc)),
            reverse=True,
        )[:max_items]
    return kept


@dataclass
class SourceRunResult:
    """Per-source outcome of a run (task 011 defect 2: fetched / new / skipped / error).

    The counts are deliberately distinct, because "this source contributed 0 rows" has several
    very different causes and conflating them is the blind spot Task 011 exists to close:

    * `fetched_count` — what the fetcher returned, before any capping. 0 here means the feed
      itself gave us nothing (dead URL, an HTML page that parses to no entries, or a token-gated
      source skipped for want of GITHUB_TOKEN — see `needs_token`).
    * `item_count`    — what survived the recency cap and was handed to storage. `fetched_count`
      high but `item_count` 0 means the source is healthy and simply publishes less often than
      SOURCE_MAX_AGE_DAYS; that is not a broken source.
    * `new_count`     — rows actually persisted to SQLite. Filled in by the storage pipeline
      after `persist_new_items`; it stays None for a bare `run_ingestion` with no persistence.
    * `skipped_count` — items seen but not stored: dropped by the cap, or already in SQLite.
    * `needs_token`   — the source is token-gated and the token is absent. Skipped, not broken.
    """

    source_name: str
    source_type: SourceType
    ok: bool
    item_count: int = 0
    error: str | None = None
    fetched_count: int = 0
    new_count: int | None = None
    needs_token: bool = False

    @property
    def skipped_count(self) -> int:
        """Fetched but not stored — capped away, or already present in SQLite."""
        stored = self.item_count if self.new_count is None else self.new_count
        return max(self.fetched_count - stored, 0)

    @property
    def zero_yield(self) -> bool:
        """Nothing reached storage this run — the condition the health warning counts."""
        return self.item_count == 0


@dataclass
class IngestionRun:
    """The whole run: every collected item plus a per-source report."""

    items: list[RawItem] = field(default_factory=list)
    results: list[SourceRunResult] = field(default_factory=list)

    @property
    def succeeded(self) -> list[SourceRunResult]:
        return [r for r in self.results if r.ok]

    @property
    def failed(self) -> list[SourceRunResult]:
        return [r for r in self.results if not r.ok]


def run_ingestion(
    sources: list[Source],
    fetchers: dict[SourceType, Fetcher] | None = None,
    *,
    max_age_days: int | None = None,
    max_items: int | None = None,
    now: datetime | None = None,
) -> IngestionRun:
    """Fetch every *enabled* source, isolating failures and applying the recency cap. Never raises.

    `fetchers` is injectable for testing; it defaults to the real registry. The recency cap
    (`max_age_days` / `max_items`, defaulting to settings) is applied per source so archive feeds
    can't blow up a run.
    """
    registry = fetchers if fetchers is not None else FETCHERS
    max_age_days = settings.source_max_age_days if max_age_days is None else max_age_days
    max_items = settings.source_max_items if max_items is None else max_items
    run = IngestionRun()

    for source in sources:
        if not source.enabled:
            continue

        # A token-gated source with no token is SKIPPED by design, not broken — record the reason
        # so the health view never sends the human to fix a URL that is fine.
        token_gated = needs_github_token(source)

        fetcher = registry.get(source.source_type)
        if fetcher is None:
            # Should be unreachable (registry covers every SourceType), but fail safe anyway.
            message = f"no fetcher registered for source_type '{source.source_type.value}'"
            logger.warning("source '%s': %s", source.name, message)
            run.results.append(
                SourceRunResult(source.name, source.source_type, ok=False, error=message,
                                needs_token=token_gated)
            )
            continue

        try:
            items = fetcher(source)
        except Exception as exc:  # noqa: BLE001 — deliberate per-source isolation
            logger.warning(
                "source '%s' (%s) failed: %s", source.name, source.source_type.value, exc
            )
            run.results.append(
                SourceRunResult(
                    source.name, source.source_type, ok=False, error=f"{type(exc).__name__}: {exc}",
                    needs_token=token_gated,
                )
            )
            continue

        fetched = len(items)
        items = apply_recency_cap(items, max_age_days=max_age_days, max_items=max_items, now=now)
        run.items.extend(items)
        run.results.append(
            SourceRunResult(
                source.name, source.source_type, ok=True, item_count=len(items),
                fetched_count=fetched, needs_token=token_gated,
            )
        )
        if len(items) != fetched:
            logger.info(
                "source '%s' (%s): %d item(s) (recency cap: %d fetched → %d kept)",
                source.name, source.source_type.value, len(items), fetched, len(items),
            )
        else:
            logger.info(
                "source '%s' (%s): %d item(s)", source.name, source.source_type.value, len(items)
            )

    return run
