"""Ingestion orchestrator — run the registry into in-memory RawItems, fail-safe per source.

The single invariant this module exists to guarantee: **one bad source never aborts the run.**
Each source is fetched in isolation; any exception is caught, logged, and recorded as a failed
`SourceRunResult`, and the run carries on. The result reports which sources succeeded and which
failed (with the reason), alongside the collected items.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.ingestion.fetchers import FETCHERS, Fetcher
from app.schemas.raw_item import RawItem
from app.schemas.source import Source, SourceType

logger = logging.getLogger(__name__)


@dataclass
class SourceRunResult:
    """Per-source outcome of a run."""

    source_name: str
    source_type: SourceType
    ok: bool
    item_count: int = 0
    error: str | None = None


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
) -> IngestionRun:
    """Fetch every *enabled* source, isolating failures. Never raises for a bad source.

    `fetchers` is injectable for testing; it defaults to the real registry.
    """
    registry = fetchers if fetchers is not None else FETCHERS
    run = IngestionRun()

    for source in sources:
        if not source.enabled:
            continue

        fetcher = registry.get(source.source_type)
        if fetcher is None:
            # Should be unreachable (registry covers every SourceType), but fail safe anyway.
            message = f"no fetcher registered for source_type '{source.source_type.value}'"
            logger.warning("source '%s': %s", source.name, message)
            run.results.append(
                SourceRunResult(source.name, source.source_type, ok=False, error=message)
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
                    source.name, source.source_type, ok=False, error=f"{type(exc).__name__}: {exc}"
                )
            )
            continue

        run.items.extend(items)
        run.results.append(
            SourceRunResult(
                source.name, source.source_type, ok=True, item_count=len(items)
            )
        )
        logger.info(
            "source '%s' (%s): %d item(s)", source.name, source.source_type.value, len(items)
        )

    return run
