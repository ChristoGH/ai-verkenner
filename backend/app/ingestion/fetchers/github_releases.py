"""GitHub releases fetcher (via the official GitHub REST API over httpx).

Curated, not a crawler: it only reads the releases of the `repo_owner/repo_name` declared in the
registry. `parse_github_releases` is split out so it can be tested on a recorded JSON payload.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from app.core.config import settings
from app.schemas.raw_item import RawItem
from app.schemas.source import Source

logger = logging.getLogger(__name__)

_API = "https://api.github.com/repos/{owner}/{repo}/releases"


def releases_url(source: Source) -> str:
    """Build the GitHub releases API URL for a source."""
    return _API.format(owner=source.repo_owner, repo=source.repo_name)


def _published_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        # GitHub timestamps are ISO-8601 with a trailing 'Z'.
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_github_releases(payload: list[dict], source: Source) -> list[RawItem]:
    """Turn the releases JSON array into RawItems, preserving each release's html_url."""
    items: list[RawItem] = []
    for release in payload:
        # Prefer the release's own page; fall back to the source URL so a URL is always present.
        url = (release.get("html_url") or source.url).strip()
        title = (release.get("name") or release.get("tag_name") or "(unnamed release)").strip()
        items.append(
            RawItem(
                source_name=source.name,
                source_type=source.source_type,
                title=title,
                url=url,
                published_at=_published_at(release.get("published_at")),
                summary=release.get("body"),
            )
        )
    return items


def fetch_github_releases(source: Source) -> list[RawItem]:
    """Fetch a repo's releases. Raises on transport/HTTP error (caller isolates)."""
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = httpx.get(
        releases_url(source),
        headers=headers,
        timeout=settings.http_timeout,
        follow_redirects=True,
    )
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, list):
        raise ValueError(f"unexpected GitHub releases payload (expected a list): {type(payload)}")
    return parse_github_releases(payload, source)
