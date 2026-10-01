"""Task 013 — the Weak Signal of the Week names the QUIETEST corroborated driver, never a hub.

Offline and deterministic (no DB, no graph store, no LLM): drives the real selection path
`sections.coherent_cluster` / `build_sections` → `posts.generate_posts`.

The regression being pinned (D-024, measured 2026-07-14 → 07-21): with shared-driver grouping in
place, `coherent_cluster` still selected the **largest** group, which on a hub-shaped corpus is the
loudest entity — OpenAI, 12 items — producing *"OpenAI is quietly converging across 7 independent
sources"*. A weak signal is corroborated but **not yet loud**, so group size was the inverse of the
product's own definition (D-026). Defect B pins the second half of the ruling: generic concept nodes
("AI", "LLM", "Large language models") are the category, not an entity within it, and may never be
the face of a weak signal.
"""

from __future__ import annotations

from app.core.config import settings
from app.digests.sections import coherent_cluster
from app.posts import PIECE_WEAK_SIGNAL, SURFACE_LINKEDIN, SURFACE_MEDIUM, SURFACE_X, generate_posts
from tests.posts_fixtures import _item

from .test_cluster_coherence import _sections

_WEAK_SURFACES = (SURFACE_X, SURFACE_LINKEDIN, SURFACE_MEDIUM)


def _driven(event_id, *, driver, driver_uid, mentions,
            pubs=("VentureBeat", "The Register", "MIT TR"),
            graph_score=0.5, priority_class="horizon_signal"):
    """A horizon item converging on `driver`, whose ambient corpus volume is `mentions`.

    Three publishers by default so the driver clears `WEAK_DRIVER_MIN_SOURCES` (task 013 defect C).
    These tests are about the *ordering* — quietest wins, stoplist excludes, ties resolve stably —
    so their candidates must be selectable at all; the floor itself is pinned separately below.
    """
    return _item(
        event_id,
        title=f"Headline {event_id} about {driver}",
        source_name=pubs[0],
        source_url=f"https://pub{event_id}.example/item{event_id}",
        priority_class=priority_class,
        summary=f"Source fact {event_id}.",
        why_it_matters=f"Interpretation of item {event_id}.",
        graph_score=graph_score,
        convergence=len(pubs),
        contributing_sources=pubs,
        coverage_sources=pubs,   # the item's own publishers — what the published count reads (016)
        driver=driver,
        driver_uid=driver_uid,
        driver_mentions=mentions,
    )


def _one(bundle, surface, piece=PIECE_WEAK_SIGNAL):
    return next(d for d in bundle.drafts if d.surface == surface and d.piece == piece)


# ---- Defect A: quietest eligible driver wins ----


def test_quietest_eligible_driver_wins():
    """A 3-item cluster on a quiet driver beats a 12-item cluster on a hub (the D-024 shape)."""
    hub = [_driven(i, driver="OpenAI", driver_uid=101, mentions=18, graph_score=0.9)
           for i in range(1, 13)]
    quiet = [_driven(50 + i, driver="state-ledger runtime", driver_uid=202, mentions=3)
             for i in range(3)]

    cluster, driver = coherent_cluster([*hub, *quiet], min_items=2)
    assert driver == "state-ledger runtime", "largest group won — the D-024 inversion is back"
    assert {it.event_id for it in cluster} == {50, 51, 52}
    assert len(cluster) < len(hub)              # explicitly: the smaller cluster is the right one

    # And it survives all the way to the drafts — the hook names the quiet driver, not the hub.
    data = _sections([*hub, *quiet])
    assert data.weak_driver == "state-ledger runtime"
    bundle = generate_posts(data)
    assert bundle.has_convergence is True
    for surface in _WEAK_SURFACES:
        text = _one(bundle, surface).text
        assert "state-ledger runtime" in text
        assert "OpenAI" not in text, f"{surface} still fronts the loudest entity"


def test_min_items_still_enforced():
    """Quietness never buys a pass on corroboration: a singleton driver is not a cluster."""
    items = [
        _driven(1, driver="quiet singleton", driver_uid=301, mentions=1),   # quietest, but alone
        _driven(2, driver="louder pair", driver_uid=302, mentions=9),
        _driven(3, driver="louder pair", driver_uid=302, mentions=9),
    ]
    cluster, driver = coherent_cluster(items, min_items=2)
    assert driver == "louder pair"
    assert {it.event_id for it in cluster} == {2, 3}

    # With the floor raised above every group, nothing survives — the honest quiet-week answer.
    assert coherent_cluster(items, min_items=3) == ((), "")


# ---- Defect B: generic concept nodes are ineligible drivers ----


def test_concept_nodes_are_ineligible_drivers():
    """A stoplisted category is never selected — not even as the only multi-item group."""
    for concept in ("LLM", "llms", "  Large   Language   Models ", "AI", "machine learning"):
        items = [_driven(i, driver=concept, driver_uid=401, mentions=2) for i in (1, 2, 3)]
        assert coherent_cluster(items, min_items=2) == ((), ""), f"{concept!r} labelled a cluster"

    # The category loses to a real entity even when it is quieter and larger.
    mixed = [
        *[_driven(i, driver="LLMs", driver_uid=401, mentions=1) for i in (1, 2, 3, 4)],
        *[_driven(i, driver="Qwen3-Coder", driver_uid=402, mentions=6) for i in (5, 6)],
    ]
    cluster, driver = coherent_cluster(mixed, min_items=2)
    assert driver == "Qwen3-Coder"
    assert {it.event_id for it in cluster} == {5, 6}


def test_stoplist_is_configurable_and_seeded():
    """The stoplist is data in config, not a literal in the selection code."""
    seeded = {name.lower() for name in settings.weak_driver_stoplist}
    assert {"ai", "artificial intelligence", "llm", "llms", "large language model",
            "large language models", "machine learning", "ml", "deep learning",
            "neural network", "generative ai", "genai", "model", "models"} <= seeded

    # An injected stoplist overrides it — nothing about the term is special to the code.
    items = [_driven(i, driver="Qwen3-Coder", driver_uid=402, mentions=6) for i in (1, 2)]
    assert coherent_cluster(items, min_items=2, stoplist=("qwen3-coder",)) == ((), "")
    assert coherent_cluster(items, min_items=2, stoplist=())[1] == "Qwen3-Coder"


def test_all_candidates_ineligible_degrades_honestly():
    """Everything stoplisted → the quiet-week path. No converging claim, all URLs kept."""
    items = [
        *[_driven(i, driver="AI", driver_uid=401, mentions=40) for i in (1, 2, 3)],
        *[_driven(i, driver="Large language models", driver_uid=402, mentions=22) for i in (4, 5)],
    ]
    data = _sections(items)
    assert data.weak_driver == ""

    bundle = generate_posts(data)
    assert bundle.has_convergence is False
    for surface in _WEAK_SURFACES:
        draft = _one(bundle, surface)
        low = draft.text.lower()
        assert "converging" not in low, f"{surface} claims convergence over a stoplisted category"
        assert "independent sources" not in low, f"{surface} claims a shared source count"
        assert "quiet" in low, f"{surface} is missing the honest quiet-week framing"
        assert draft.source_urls
        for url in draft.source_urls:
            assert url in draft.text, f"{surface} dropped a source URL on the degraded path"


# ---- determinism ----


def test_driver_selection_is_deterministic():
    """Same corpus, same answer — including when mentions, size and score all tie."""
    items = [
        *[_driven(i, driver="Alpha", driver_uid=901, mentions=5, graph_score=0.4) for i in (1, 2)],
        *[_driven(i, driver="Beta", driver_uid=902, mentions=5, graph_score=0.4) for i in (3, 4)],
        *[_driven(i, driver="Gamma", driver_uid=903, mentions=5, graph_score=0.4) for i in (5, 6)],
    ]
    first = coherent_cluster(items, min_items=2)
    assert first[1] == "Alpha", "an exact tie must resolve on the lowest uid"
    for _ in range(5):
        assert coherent_cluster(items, min_items=2) == first
    # Input order must not move the answer either.
    assert coherent_cluster(list(reversed(items)), min_items=2)[1] == "Alpha"

    # Each tie-break level in turn: size, then summed graph score, then uid.
    by_size = [
        *[_driven(i, driver="Pair", driver_uid=911, mentions=5) for i in (1, 2)],
        *[_driven(i, driver="Trio", driver_uid=912, mentions=5) for i in (3, 4, 5)],
    ]
    assert coherent_cluster(by_size, min_items=2)[1] == "Trio"

    by_score = [
        *[_driven(i, driver="Dim", driver_uid=921, mentions=5, graph_score=0.1) for i in (1, 2)],
        *[_driven(i, driver="Bright", driver_uid=922, mentions=5, graph_score=0.8) for i in (3, 4)],
    ]
    assert coherent_cluster(by_score, min_items=2)[1] == "Bright"


# ---- Defect C: the selection floor (task 013 / D-047) ----
#
# The objective is a MINIMISER, so it lands on whatever the floor permits. At a floor of 2 the
# winner is "2 mentions / 2 sources / 2 items" by construction — coincidence, not corroboration.
# On the real corpus that fixed point was `Firefox`, one of whose two items had no AI content at
# all (D-036). A weak signal needs enough corroboration to be REAL *and* low ambient volume.


def test_floor_excludes_thin_evidence_drivers():
    """The `Firefox` regression by name: 2 sources / 2 items is never selectable, however quiet."""
    firefox = [
        _driven(i, driver="Firefox", driver_uid=561, mentions=2,
                pubs=("Simon Willison", "The Register"))          # 2 distinct sources
        for i in (1, 2)                                           # 2 items
    ]
    # Quietest by a wide margin, and the only group — and still not the weak signal.
    assert coherent_cluster(firefox, min_items=3, min_sources=3) == ((), "")

    # Each floor bites on its own: enough items but too few sources, and vice versa.
    thin_sources = [
        _driven(i, driver="Firefox", driver_uid=561, mentions=2,
                pubs=("Simon Willison", "The Register")) for i in (1, 2, 3)
    ]
    assert coherent_cluster(thin_sources, min_items=3, min_sources=3) == ((), "")
    thin_items = [_driven(i, driver="Firefox", driver_uid=561, mentions=2) for i in (1, 2)]
    assert coherent_cluster(thin_items, min_items=3, min_sources=3) == ((), "")

    # And the honest quiet-week draft ships instead of a coincidence dressed as a signal.
    data = _sections(firefox)
    assert data.weak_driver == ""
    bundle = generate_posts(data)
    assert bundle.has_convergence is False
    for surface in _WEAK_SURFACES:
        low = _one(bundle, surface).text.lower()
        assert "converging" not in low and "quiet" in low


def test_quietest_above_floor_wins():
    """The floor gates entry; quietness still decides among everything that clears it."""
    hub = [_driven(i, driver="OpenAI", driver_uid=101, mentions=17, graph_score=0.9,
                   pubs=("VentureBeat", "The Register", "MIT TR", "Hacker News",
                         "arXiv", "Ars Technica", "TechCrunch"))          # 7 sources, 12 items
           for i in range(1, 13)]
    quiet = [_driven(50 + i, driver="Claude Code", driver_uid=202, mentions=3)  # 3 sources, 3 items
             for i in range(3)]

    cluster, driver = coherent_cluster([*hub, *quiet], min_items=3, min_sources=3)
    assert driver == "Claude Code", "the floor must gate entry, not replace the quietness objective"
    assert {it.event_id for it in cluster} == {50, 51, 52}

    # End to end, at the shipped defaults — no explicit floors passed.
    data = _sections([*hub, *quiet])
    assert data.weak_driver == "Claude Code"
    assert "OpenAI" not in _one(generate_posts(data), SURFACE_LINKEDIN).text


def test_graph_min_sources_unchanged():
    """The selection floor is a SEPARATE setting; convergence scoring is provably untouched."""
    from app.graph.store import ConvergenceStat
    from app.scoring.graph_signals import _contribution

    # Two distinct settings, two different values — the selection floor never aliases the global one.
    assert settings.graph_min_sources == 2, "GRAPH_MIN_SOURCES was moved; D-026/D-047 forbid it"
    assert settings.weak_driver_min_sources == 3
    assert settings.weak_cluster_min_items == 3

    # The proof that matters: an entity on 2 distinct sources STILL scores as convergence in
    # `graph_signals` — it is merely not selectable as the face of the weak signal.
    stat = ConvergenceStat(entity_uid=1, distinct_sources=2, mentions=2, degree=3,
                           last_ts=None, event_count=2)
    contribution, _idf = _contribution(
        stat, total_developments=100, min_sources=settings.graph_min_sources,
        w_conv=1.0, w_deg=0.5,
    )
    assert contribution > 0, "raising the selection floor changed what counts as convergence"

    thin = [_driven(i, driver="Firefox", driver_uid=561, mentions=2,
                    pubs=("Simon Willison", "The Register")) for i in (1, 2, 3)]
    assert all(it.convergence >= settings.graph_min_sources for it in thin)   # still convergent…
    assert coherent_cluster(thin, min_items=3) == ((), "")                    # …just not selectable
