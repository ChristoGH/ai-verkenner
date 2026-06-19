"""Tests for the end-to-end store path `ingest_and_store` (M3).

Ingestion is monkeypatched so no network is touched; the focus is the SQLite-first ordering and
the degrade behaviour.
"""

from sqlmodel import select

from app.ingestion.orchestrator import IngestionRun, SourceRunResult
from app.models import Event, RawItem
from app.schemas.source import Source, SourceType, TrustLevel
from app.storage import pipeline
from tests.conftest import make_item


def _sources():
    return [Source(name="Feed A", source_type=SourceType.rss, url="https://a.example/feed",
                   trust_level=TrustLevel.high)]


def _canned_run(items):
    return IngestionRun(
        items=items,
        results=[SourceRunResult("Feed A", SourceType.rss, ok=True, item_count=len(items))],
    )


def _patch_ingestion(monkeypatch, items):
    monkeypatch.setattr(pipeline, "run_ingestion", lambda _sources: _canned_run(items))


def test_pipeline_persists_and_dedups(session, qdrant_mem, embedder, monkeypatch):
    items = [
        make_item("GPT-5 released by OpenAI today", "https://a.example/1",
                  summary="OpenAI ships GPT-5 today"),
        make_item("OpenAI releases GPT-5 today", "https://b.example/1",
                  summary="OpenAI ships GPT-5 today", source_name="Feed A"),
        make_item("Qdrant 1.9 adds filtering", "https://a.example/2",
                  summary="vector database release"),
    ]
    _patch_ingestion(monkeypatch, items)

    result = pipeline.ingest_and_store(
        _sources(), session=session, embedder=embedder, qdrant_client=qdrant_mem, tau=0.6
    )

    assert result.fetched_item_count == 3
    assert result.new_item_count == 3
    assert result.embedded_count == 3
    # Two near-dups → one Event; the distinct item → another. 3 items, 2 events.
    assert len(session.exec(select(RawItem)).all()) == 3
    assert len(session.exec(select(Event)).all()) == 2


def test_pipeline_rerun_adds_no_duplicates(session, qdrant_mem, embedder, monkeypatch):
    items = [make_item("Only post", "https://a.example/1", summary="hello")]
    _patch_ingestion(monkeypatch, items)

    first = pipeline.ingest_and_store(
        _sources(), session=session, embedder=embedder, qdrant_client=qdrant_mem, tau=0.6
    )
    second = pipeline.ingest_and_store(
        _sources(), session=session, embedder=embedder, qdrant_client=qdrant_mem, tau=0.6
    )

    assert first.new_item_count == 1
    assert second.new_item_count == 0
    assert len(session.exec(select(RawItem)).all()) == 1


def test_pipeline_persists_to_sqlite_even_with_qdrant_down(session, embedder, monkeypatch):
    items = [make_item("Post", "https://a.example/1", summary="body")]
    _patch_ingestion(monkeypatch, items)

    # qdrant_client=None simulates the store being unavailable.
    result = pipeline.ingest_and_store(
        _sources(), session=session, embedder=embedder, qdrant_client=None, tau=0.6
    )

    assert result.new_item_count == 1
    assert result.embedded_count == 0  # nothing embedded, but the record stands
    stored = session.exec(select(RawItem)).all()
    assert len(stored) == 1
    assert stored[0].event_id is not None
