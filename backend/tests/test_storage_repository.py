"""Tests for SQLite persistence: source upsert + idempotent item persistence (M3)."""

from sqlmodel import select

from app.models import RawItem as RawItemModel
from app.models import Source as SourceModel
from app.schemas.source import Source, SourceType, TrustLevel
from app.storage.repository import persist_new_items, upsert_sources
from tests.conftest import make_item


def _source(name="Feed A", url="https://a.example/feed") -> Source:
    return Source(
        name=name, source_type=SourceType.rss, url=url, trust_level=TrustLevel.high
    )


def test_upsert_sources_inserts_then_updates(session):
    ids = upsert_sources(session, [_source(url="https://a.example/v1")])
    assert set(ids) == {"Feed A"}

    # Re-upsert with a changed URL — same row updated, not duplicated.
    upsert_sources(session, [_source(url="https://a.example/v2")])
    rows = session.exec(select(SourceModel)).all()
    assert len(rows) == 1
    assert rows[0].url == "https://a.example/v2"


def test_persist_new_items_stores_and_preserves_url(session):
    ids = upsert_sources(session, [_source()])
    item = make_item("Hello world", "https://a.example/post-1", summary="body")
    new_rows = persist_new_items(session, [item], ids)

    assert len(new_rows) == 1
    stored = session.exec(select(RawItemModel)).all()
    assert len(stored) == 1
    assert stored[0].url == "https://a.example/post-1"  # preserved verbatim
    assert stored[0].source_id == ids["Feed A"]
    assert stored[0].dedup_key and stored[0].content_hash


def test_persist_is_idempotent_across_runs(session):
    ids = upsert_sources(session, [_source()])
    items = [
        make_item("Post one", "https://a.example/1"),
        make_item("Post two", "https://a.example/2"),
    ]
    first = persist_new_items(session, items, ids)
    assert len(first) == 2

    # Same items again → no new rows, counts don't double.
    second = persist_new_items(session, items, ids)
    assert second == []
    assert len(session.exec(select(RawItemModel)).all()) == 2


def test_persist_dedups_within_a_single_batch(session):
    ids = upsert_sources(session, [_source()])
    dup = make_item("Repeated", "https://a.example/dup")
    new_rows = persist_new_items(session, [dup, dup], ids)
    assert len(new_rows) == 1
    assert len(session.exec(select(RawItemModel)).all()) == 1


def test_same_story_two_sources_keeps_both_rows(session):
    ids = upsert_sources(
        session,
        [_source("Feed A", "https://a.example/feed"), _source("Feed B", "https://b.example/feed")],
    )
    items = [
        make_item("Model X ships", "https://a.example/x", source_name="Feed A"),
        make_item("Model X ships", "https://b.example/x", source_name="Feed B"),
    ]
    new_rows = persist_new_items(session, items, ids)
    # Different URLs → distinct identity keys → both rows kept (grouped later by Event).
    assert len(new_rows) == 2
