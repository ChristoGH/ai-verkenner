"""Tests for two-stage dedup → Events, degrade paths, and reindex (M3).

Offline + deterministic: in-memory SQLite, in-process Qdrant, HashingEmbedder. The hashing
embedder gives within-cluster cosine ~0.76–0.91 and cross-cluster ~0.0 for the fixture below, so
`tau=0.6` merges the cluster with a wide no-false-merge margin.
"""

from sqlmodel import select

from app.db import qdrant_index
from app.models import Event, RawItem
from app.schemas.source import Source, SourceType, TrustLevel
from app.storage.dedup import assign_events, reindex
from app.storage.repository import persist_new_items, upsert_sources
from tests.conftest import make_item

TAU = 0.6

# One development, three near-duplicate wordings + two distinct items.
_CLUSTER = [
    ("OpenAI releases GPT-5 with major reasoning gains",
     "OpenAI announced GPT-5 today, citing major reasoning improvements"),
    ("GPT-5 launched by OpenAI, big reasoning improvements",
     "OpenAI has launched GPT-5 with major gains in reasoning"),
    ("OpenAI GPT-5 release: major reasoning improvements",
     "Today OpenAI released GPT-5 with major reasoning gains"),
]
_DISTINCT = [
    ("Qdrant 1.9 adds new payload filtering",
     "The Qdrant vector database ships 1.9 with filtering"),
    ("Neo4j publishes graph data science update",
     "Neo4j announces a graph data science library release"),
]


def _seed_sources(session):
    return upsert_sources(
        session,
        [Source(name="Feed A", source_type=SourceType.rss, url="https://a.example/feed",
                trust_level=TrustLevel.high)],
    )


def _items_for(entries, prefix):
    return [
        make_item(title, f"https://a.example/{prefix}-{i}", summary=summary)
        for i, (title, summary) in enumerate(entries)
    ]


def test_ann_groups_near_dups_with_no_false_merge(session, qdrant_mem, embedder):
    ids = _seed_sources(session)
    items = _items_for(_CLUSTER + _DISTINCT, "n")
    rows = persist_new_items(session, items, ids)

    assign_events(session, rows, qdrant_client=qdrant_mem, embedder=embedder, tau=TAU)

    rows = session.exec(select(RawItem).order_by(RawItem.id)).all()
    cluster_events = {r.event_id for r in rows[:3]}
    distinct_events = [r.event_id for r in rows[3:]]

    # The three near-dups share exactly one Event.
    assert len(cluster_events) == 1
    # The two distinct items are each their own Event — and NOT the cluster's (no false-merge).
    assert len(set(distinct_events)) == 2
    assert cluster_events.isdisjoint(distinct_events)
    # Three real-world developments → three Events; every item embedded.
    assert len(session.exec(select(Event)).all()) == 3
    assert all(r.embedded for r in rows)


def test_degrades_to_hash_only_when_qdrant_absent(session, embedder):
    """With no Qdrant: identical-content items still merge (stage a); near-dups do not."""
    ids = _seed_sources(session)
    identical_a = make_item("Model X ships", "https://a.example/1", summary="Lab Y ships Model X")
    identical_b = make_item("Model X ships", "https://b.example/1", summary="Lab Y ships Model X",
                            source_name="Feed A")
    near_dup = make_item("Model X has shipped from Lab Y", "https://a.example/2",
                         summary="Lab Y has now shipped Model X to users")
    rows = persist_new_items(session, [identical_a, identical_b, near_dup], ids)

    assign_events(session, rows, qdrant_client=None, embedder=embedder, tau=TAU)

    rows = session.exec(select(RawItem).order_by(RawItem.id)).all()
    # Identical content collapses; the differently-worded near-dup stays separate without ANN.
    assert rows[0].event_id == rows[1].event_id
    assert rows[2].event_id != rows[0].event_id
    # No embeddings were written.
    assert not any(r.embedded for r in rows)


def test_sqlite_record_survives_qdrant_write_failure(session, qdrant_mem, embedder, monkeypatch):
    """A Qdrant upsert failure must not lose the SQLite record (ADR 0001)."""
    ids = _seed_sources(session)
    items = _items_for(_CLUSTER, "f")
    rows = persist_new_items(session, items, ids)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated qdrant write failure")

    monkeypatch.setattr(qdrant_index, "upsert_item", _boom)

    # Must not raise.
    assign_events(session, rows, qdrant_client=qdrant_mem, embedder=embedder, tau=TAU)

    stored = session.exec(select(RawItem).order_by(RawItem.id)).all()
    # Every record persisted; each got an Event; none marked embedded (embeddable-later).
    assert len(stored) == 3
    assert all(r.event_id is not None for r in stored)
    assert not any(r.embedded for r in stored)


def test_reindex_rebuilds_qdrant_from_sqlite(session, qdrant_mem, embedder):
    ids = _seed_sources(session)
    rows = persist_new_items(session, _items_for(_CLUSTER + _DISTINCT, "r"), ids)
    assign_events(session, rows, qdrant_client=qdrant_mem, embedder=embedder, tau=TAU)

    # Wipe the derived index entirely, then rebuild it purely from SQLite.
    qdrant_mem.delete_collection(qdrant_index.ITEMS_COLLECTION)
    count = reindex(session, qdrant_client=qdrant_mem, embedder=embedder)

    assert count == 5
    info = qdrant_mem.get_collection(qdrant_index.ITEMS_COLLECTION)
    assert info.points_count == 5
    # The rebuilt index still finds the cluster: a cluster vector retrieves its near-dups.
    from app.storage.hashing import embedding_text
    vec = embedder.embed([embedding_text(*_CLUSTER[0])])[0]
    hits = qdrant_index.search_neighbours(qdrant_mem, vec, limit=5, score_threshold=TAU)
    assert len(hits) >= 3  # the three near-dups come back together


def test_assign_events_is_stable_on_rerun(session, qdrant_mem, embedder):
    ids = _seed_sources(session)
    rows = persist_new_items(session, _items_for(_CLUSTER, "s"), ids)
    assign_events(session, rows, qdrant_client=qdrant_mem, embedder=embedder, tau=TAU)
    before = {r.id: r.event_id for r in session.exec(select(RawItem)).all()}

    # A re-persist of the same items yields no new rows; re-running assign on the (empty) new set
    # leaves every existing assignment untouched.
    new_rows = persist_new_items(session, _items_for(_CLUSTER, "s"), ids)
    assert new_rows == []
    assign_events(session, new_rows, qdrant_client=qdrant_mem, embedder=embedder, tau=TAU)

    after = {r.id: r.event_id for r in session.exec(select(RawItem)).all()}
    assert before == after
