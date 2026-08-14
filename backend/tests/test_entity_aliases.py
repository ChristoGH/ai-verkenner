"""Task 014 — one concept, one uid.

Offline and deterministic: SQLite + the in-memory graph store, no Neo4j, no LLM. These drive the
real projection path (`graph.projection.project_event` / `graph_reindex`), so they pin shipped
behaviour rather than the resolver in isolation.

The defect being pinned (D-024, measured 2026-07-14 → 07-21): "AI", "LLM", "LLMs", "Large language
models" and "Artificial Intelligence" were **five entity uids for one concept**. That inflates the
driver count and — the damaging half — splits items that genuinely converge on one entity across
alias uids, dropping real clusters below `WEAK_CLUSTER_MIN_ITEMS`. A false-negative generator.

The sequencing pinned here is the whole reason task 013 had to merge first (D-026): the merged
concept node is *larger*, so it must still be ineligible to label a weak signal.
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings
from app.digests.sections import _eligible_driver
from app.graph.aliases import AliasMap, EntityResolver, load_alias_map
from app.graph import InMemoryGraph
from app.graph.projection import graph_reindex, project_event
from app.graph.util import ENTITY
from app.models import Entity
from app.schemas.enrichment import normalise_entity_name
from tests import graph_helpers as gh

# The concept family D-024 measured, plus a vendor-spelling pair.
_CONCEPT_FAMILY = ("AI", "Artificial Intelligence", "LLM", "LLMs", "Large language models")


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _entity_nodes(store: InMemoryGraph) -> dict:
    """{uid: props} for every Entity node in the store (InMemoryGraph nests props under "props")."""
    return {uid: node["props"] for (label, uid), node in store.nodes.items() if label == ENTITY}


def _seed_family(session, store, names, *, subject_of="Qdrant") -> list[Entity]:
    """One Event per name, each mentioning that surface form — the fragmentation shape."""
    other = gh.add_entity(session, subject_of, "tool")
    entities = []
    for n, name in enumerate(names):
        src = gh.add_source(session, f"pub{n}")
        ev = gh.add_event(session, f"development {n}")
        item = gh.add_item(session, src, ev, title=f"item {n}", url=f"https://pub{n}.example/{n}")
        entity = gh.add_entity(session, name, "concept")
        gh.add_relationship(session, entity, "relates_to", other, event=ev, item=item)
        gh.add_enriched(session, ev, item, priority_class="horizon_signal")
        entities.append(entity)
    return entities


# ---- the merge itself ----


def test_alias_map_collapses_concept_family(session):
    """The five surface forms D-024 found project onto ONE canonical entity node."""
    store = InMemoryGraph()
    _seed_family(session, store, _CONCEPT_FAMILY)
    graph_reindex(session, store)

    # Five Entity rows in SQLite — nothing is deleted or rewritten there (ADR 0001).
    concept_rows = session.exec(select(Entity).where(Entity.type == "concept")).all()
    assert len(concept_rows) == len(_CONCEPT_FAMILY)

    # One node in the graph, carrying the canonical display name.
    nodes = _entity_nodes(store)
    concept_uids = {uid for uid, props in nodes.items()
                    if props.get("type") == "concept"}
    assert len(concept_uids) == 1, f"concept family did not merge: {nodes}"
    canonical = nodes[concept_uids.pop()]
    assert canonical["name"] == "AI"

    # And the resolver agrees for every member, so downstream uid grouping sees one driver.
    resolver = EntityResolver(session)
    assert len({resolver.resolve(e.id) for e in concept_rows}) == 1
    assert resolver.merged_count == len(_CONCEPT_FAMILY) - 1


def test_fragmented_cluster_merges_into_one_driver(session):
    """The false-negative fix: three items that were three 1-item drivers become one 3-item driver.

    This is the harm that matters. Count reduction is cosmetic; a genuine convergence falling below
    `WEAK_CLUSTER_MIN_ITEMS` because publishers spell a vendor differently is a missed signal.
    """
    store = InMemoryGraph()
    spellings = ("OpenAI", "Open AI", "OpenAI Inc")
    rows = _seed_family(session, store, spellings)
    graph_reindex(session, store)

    resolver = EntityResolver(session)
    drivers = {resolver.resolve(r.id) for r in rows}
    assert len(drivers) == 1, "three spellings of one vendor are still three drivers"

    # The merged node accumulates the mentions that were previously split one apiece.
    stats = {s.entity_uid: s for s in store.convergence(None)}
    merged = stats[drivers.pop()]
    assert merged.distinct_sources == len(spellings)     # was 1 per fragment
    assert merged.event_count == len(spellings)          # was 1 per fragment


# ---- the 013 interaction: this is why the sequencing is load-bearing ----


def test_canonical_concept_still_stoplisted(session):
    """The MERGED concept node must remain ineligible to label a weak signal (D-026 sequencing).

    Normalisation makes the category node bigger. If task 013's stoplist stopped catching it, this
    task would have made the original defect worse, which is exactly what the ordering prevents.
    """
    blocked = {normalise_entity_name(n) for n in settings.weak_driver_stoplist}
    alias_map = load_alias_map()

    for surface_form in _CONCEPT_FAMILY:
        canonical = alias_map.canonical_name(surface_form)
        assert not _eligible_driver(canonical, blocked), (
            f"{surface_form!r} merges to {canonical!r}, which is NOT stoplisted — "
            "the merged hub could now label a weak signal"
        )


# ---- properties of the resolution ----


def test_unmapped_entities_pass_through_unchanged(session):
    """Nothing outside the curated map is touched — no fuzzy matching, no accidental merging."""
    store = InMemoryGraph()
    names = ("Qdrant Cloud", "Weaviate", "pgvector", "Bias", "Bia")
    rows = _seed_family(session, store, names, subject_of="Some Other Thing")
    graph_reindex(session, store)

    resolver = EntityResolver(session)
    for row in rows:
        assert resolver.resolve(row.id) == row.id, f"{row.name!r} was merged and should not be"
        assert resolver.display_name(row.id, row.name) == row.name

    nodes = _entity_nodes(store)
    projected = {props["name"] for props in nodes.values() if props.get("type") == "concept"}
    assert projected == set(names)

    # The trailing-`s` fold is a map LOOKUP aid, never a licence to merge two unlisted entities.
    assert resolver.resolve(rows[3].id) != resolver.resolve(rows[4].id)


def test_normalisation_is_idempotent(session):
    """Reindexing twice yields identical entity identities and node properties."""
    store = InMemoryGraph()
    _seed_family(session, store, _CONCEPT_FAMILY)

    graph_reindex(session, store)
    first = dict(_entity_nodes(store))
    counts_first = store.counts()

    graph_reindex(session, store)
    assert _entity_nodes(store) == first
    assert store.counts() == counts_first


def test_reindex_rebuilds_from_sqlite_alone(session):
    """The normalised graph is a derived index: clear it, rebuild it, get the same thing (ADR 0001).

    Also pins that the rebuild does not depend on prior graph state — a fresh store reaches the
    identical result, which is what makes Neo4j disposable.
    """
    store = InMemoryGraph()
    _seed_family(session, store, _CONCEPT_FAMILY)
    graph_reindex(session, store)
    expected = dict(_entity_nodes(store))

    fresh = InMemoryGraph()
    graph_reindex(session, fresh)
    assert _entity_nodes(fresh) == expected
    assert fresh.counts() == store.counts()


def test_alias_map_degrades_when_absent(tmp_path, session):
    """A missing alias file means "normalise nothing", not a broken run (fail-safe, per source)."""
    empty = load_alias_map(tmp_path / "does-not-exist.yaml")
    assert empty.is_empty
    assert empty.canonical_name("LLMs") == "LLMs"

    store = InMemoryGraph()
    rows = _seed_family(session, store, _CONCEPT_FAMILY)
    resolver = EntityResolver(session, alias_map=empty)
    for event_id in {r.id for r in rows}:
        assert resolver.resolve(event_id) == event_id
    assert resolver.merged_count == 0


def test_alias_map_matches_on_normalised_identity():
    """Case, whitespace and a trailing plural are folded; the map itself stays exact-match."""
    alias_map = AliasMap(canonical_by_key={"open ai": "OpenAI", "llm": "AI"})
    for form in ("Open AI", "open  ai", "OPEN AI", "  Open AI  "):
        assert alias_map.canonical_name(form) == "OpenAI"
    assert alias_map.canonical_name("LLMs") == "AI"          # trailing-s fold finds the key
    assert alias_map.canonical_name("Openai") == "Openai"    # not a listed form → unchanged
