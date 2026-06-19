"""arXiv fetcher (via the arXiv Atom API over httpx, parsed with feedparser).

The arXiv API returns an Atom feed, so we fetch with httpx (timeout + user agent) and reuse
feedparser to parse it. `build_arxiv_url` is split out and unit-tested.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import feedparser
import httpx

from app.core.config import settings
from app.schemas.raw_item import RawItem
from app.schemas.source import Source

logger = logging.getLogger(__name__)

_API = "http://export.arxiv.org/api/query"


def build_arxiv_url(source: Source, max_results: int | None = None) -> str:
    """Build the arXiv API query URL for a source, newest first."""
    if not source.arxiv_query:
        raise ValueError("arxiv source is missing 'arxiv_query'")
    params = {
        "search_query": source.arxiv_query,
        "start": 0,
        "max_results": max_results if max_results is not None else settings.arxiv_max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    return f"{_API}?{urlencode(params)}"


def _published_at(entry: feedparser.FeedParserDict) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is None:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)


def parse_arxiv(content: bytes, source: Source) -> list[RawItem]:
    """Parse an arXiv Atom response into RawItems, preserving each paper's link."""
    feed = feedparser.parse(content)
    items: list[RawItem] = []
    for entry in feed.entries:
        url = (entry.get("link") or source.url).strip()
        title = " ".join((entry.get("title") or "(untitled)").split())
        items.append(
            RawItem(
                source_name=source.name,
                source_type=source.source_type,
                title=title,
                url=url,
                published_at=_published_at(entry),
                summary=entry.get("summary"),
            )
        )
    return items


def fetch_arxiv(source: Source) -> list[RawItem]:
    """Fetch and parse an arXiv query. Raises on transport/HTTP error (caller isolates)."""
    headers = {"User-Agent": settings.user_agent}
    resp = httpx.get(
        build_arxiv_url(source),
        headers=headers,
        timeout=settings.http_timeout,
        follow_redirects=True,
    )
    resp.raise_for_status()
    return parse_arxiv(resp.content, source)
