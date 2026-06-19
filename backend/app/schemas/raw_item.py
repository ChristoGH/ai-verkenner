"""The `RawItem` shape produced by ingestion.

A `RawItem` is the unenriched output of fetching one source: the fact, before any dedup,
enrichment, or scoring. **Its `url` is always preserved** — a surfaced item without its source
link is a bug (core invariant). Nothing is persisted at M1; these live in memory only.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.source import SourceType


class RawItem(BaseModel):
    """One fetched item, carrying a reference to the source that produced it."""

    source_name: str
    source_type: SourceType
    title: str
    # The item's canonical link (article / release / paper). ALWAYS preserved.
    url: str
    published_at: datetime | None = None
    summary: str | None = None

    @field_validator("url")
    @classmethod
    def _url_required(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("RawItem.url must be present — every item keeps its source link")
        return value
