"""Shared fixtures for the M3 storage/dedup tests.

Everything here is offline and deterministic: an in-memory SQLite DB, an in-process Qdrant
(`:memory:`), and the `HashingEmbedder` (no model download, ever).
"""

from __future__ import annotations

import pytest
from qdrant_client import QdrantClient
from sqlmodel import Session

from app.db.sqlite import init_db, make_engine
from app.embeddings import HashingEmbedder
from app.schemas.raw_item import RawItem
from app.schemas.source import SourceType


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")  # shared in-memory DB (StaticPool)
    init_db(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def qdrant_mem():
    """A real, in-process Qdrant — full ANN behaviour, no server, no network."""
    client = QdrantClient(location=":memory:")
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def embedder():
    return HashingEmbedder(dim=256)


def make_item(
    title: str,
    url: str,
    *,
    source_name: str = "Feed A",
    summary: str | None = None,
    source_type: SourceType = SourceType.rss,
) -> RawItem:
    """Build a RawItem schema for tests."""
    return RawItem(
        source_name=source_name,
        source_type=source_type,
        title=title,
        url=url,
        summary=summary,
    )
