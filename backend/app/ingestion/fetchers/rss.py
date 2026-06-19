"""RSS / Atom fetcher.

Fetch bytes over httpx (so we control the timeout and user agent), then parse with feedparser.
Splitting `parse_rss` from `fetch_rss` keeps parsing unit-testable on a fixture without a network
call.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import struct_time

import feedparser
import httpx

from app.core.config import settings
from app.schemas.raw_item import RawItem
from app.schemas.source import Source

logger = logging.getLogger(__name__)


def _published_at(entry: feedparser.FeedParserDict) -> datetime | None:
    parsed: struct_time | None = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is None:
        return None
    # feedparser normalises to UTC; build a tz-aware datetime.
    return datetime(*parsed[:6], tzinfo=timezone.utc)


def parse_rss(content: bytes, source: Source) -> list[RawItem]:
    """Parse feed bytes into RawItems, preserving each entry's link."""
    feed = feedparser.parse(content)
    items: list[RawItem] = []
    for entry in feed.entries:
        # Preserve the source link: prefer the entry's own link; fall back to the source URL so
        # the item never loses a URL (core invariant).
        url = (entry.get("link") or source.url).strip()
        title = (entry.get("title") or "(untitled)").strip()
        summary = entry.get("summary")
        items.append(
            RawItem(
                source_name=source.name,
                source_type=source.source_type,
                title=title,
                url=url,
                published_at=_published_at(entry),
                summary=summary,
            )
        )
    return items


def fetch_rss(source: Source) -> list[RawItem]:
    """Fetch and parse an RSS/Atom source. Raises on transport/HTTP error (caller isolates)."""
    headers = {"User-Agent": settings.user_agent}
    resp = httpx.get(
        source.url, headers=headers, timeout=settings.http_timeout, follow_redirects=True
    )
    resp.raise_for_status()
    return parse_rss(resp.content, source)
