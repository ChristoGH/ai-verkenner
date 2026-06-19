"""Stubs for the curated GitHub-intelligence source types (ADR 0002).

`github_star_velocity`, `github_new_repos`, `github_advisories`, and `github_changes` are
registered now (M1) so `sources.yaml` can declare them and the registry can validate them, but
their real fetchers land in **M3** (ingest + embed + dedup), where they feed the convergence
signal. Until then each is a clean no-op: it logs "not yet implemented (M3)" and returns no items,
so a run that includes one neither fails nor invents data.
"""

from __future__ import annotations

import logging

from app.schemas.raw_item import RawItem
from app.schemas.source import Source

logger = logging.getLogger(__name__)


def _not_yet_implemented(source: Source) -> list[RawItem]:
    logger.info(
        "source '%s' (%s): GitHub-intelligence fetcher not yet implemented (M3) — skipping",
        source.name,
        source.source_type.value,
    )
    return []


def fetch_github_star_velocity(source: Source) -> list[RawItem]:
    return _not_yet_implemented(source)


def fetch_github_new_repos(source: Source) -> list[RawItem]:
    return _not_yet_implemented(source)


def fetch_github_advisories(source: Source) -> list[RawItem]:
    return _not_yet_implemented(source)


def fetch_github_changes(source: Source) -> list[RawItem]:
    return _not_yet_implemented(source)
