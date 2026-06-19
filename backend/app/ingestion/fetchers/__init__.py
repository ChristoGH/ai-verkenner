"""Fetcher registry: one callable per `SourceType`.

A fetcher takes a `Source` and returns a list of `RawItem`s, or **raises** on failure. Failure
isolation is the orchestrator's job (it catches and reports), never the fetcher's — this keeps
each fetcher simple and honest about errors.
"""

from __future__ import annotations

from collections.abc import Callable

from app.ingestion.fetchers.arxiv import fetch_arxiv
from app.ingestion.fetchers.github_intelligence import (
    fetch_github_advisories,
    fetch_github_changes,
    fetch_github_new_repos,
    fetch_github_star_velocity,
)
from app.ingestion.fetchers.github_releases import fetch_github_releases
from app.ingestion.fetchers.rss import fetch_rss
from app.schemas.raw_item import RawItem
from app.schemas.source import Source, SourceType

Fetcher = Callable[[Source], list[RawItem]]

# Every SourceType maps to a fetcher. The GitHub-intelligence types map to M3 stubs that no-op.
FETCHERS: dict[SourceType, Fetcher] = {
    SourceType.rss: fetch_rss,
    SourceType.github_releases: fetch_github_releases,
    SourceType.arxiv: fetch_arxiv,
    SourceType.github_star_velocity: fetch_github_star_velocity,
    SourceType.github_new_repos: fetch_github_new_repos,
    SourceType.github_advisories: fetch_github_advisories,
    SourceType.github_changes: fetch_github_changes,
}

__all__ = ["FETCHERS", "Fetcher"]
