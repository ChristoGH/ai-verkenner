"""Task 010 Defect 1 — a convergence may be claimed only for items sharing ONE driving entity.

Offline and deterministic (no DB, no graph store, no LLM): drives the real selection path
`sections.build_sections` → `posts.generate_posts`, so these pin the shipped behaviour rather than a
helper in isolation.

The regression being pinned (M7.5, 2026-07-21): `sections.py` filtered on the **per-item** property
`convergence > 0` — "this item's own driver crossed >= GRAPH_MIN_SOURCES sources" — which collected
eight items each converging on a *different* entity and published them as one cluster, labelled with
one publisher's headline and credited with the union of nine unrelated publishers.
"""

from __future__ import annotations

from app.digests.sections import DigestData, build_sections, coherent_cluster
from app.posts import (
    PIECE_NOISE_REPORT,
    PIECE_WEAK_SIGNAL,
    SURFACE_LINKEDIN,
    SURFACE_MEDIUM,
    SURFACE_X,
    generate_posts,
    weak_cluster,
)
from tests.posts_fixtures import (
    DRIVER,
    DRIVER_UID,
    _empty_sections,
    _item,
    _noise_items,
    converging_digest,
    thin_digest,
)

_WEAK_SURFACES = (SURFACE_X, SURFACE_LINKEDIN, SURFACE_MEDIUM)

# Three publishers, so a cluster built from these items clears the selection floor added by task 013
# defect C (`WEAK_DRIVER_MIN_SOURCES` = 3). These tests pin MEMBERSHIP — that a cluster requires one
# shared driver — so their fixtures have to be selectable before membership can be observed at all.
_PUBS = ("VentureBeat", "The Register", "MIT TR")


def _one(bundle, surface, piece=PIECE_WEAK_SIGNAL):
    return next(d for d in bundle.drafts if d.surface == surface and d.piece == piece)


def _sections(items) -> DigestData:
    """Run the real section router over these items (pure: no signals map needed for the quadrant)."""
    return build_sections(items, {}, high_hype=4, section_limit=8, graphrag=True,
                          period_start=None, period_end=None)


def _converger(event_id, *, driver, driver_uid, pubs, priority_class="horizon_signal"):
    """A horizon item whose OWN driver converged — the per-item property the old filter used."""
    return _item(
        event_id,
        title=f"Headline {event_id} about {driver}",
        source_name=pubs[0],
        source_url=f"https://pub{event_id}.example/item{event_id}",
        priority_class=priority_class,
        summary=f"Source fact {event_id}.",
        why_it_matters=f"Interpretation of item {event_id}.",
        graph_score=1.0 - event_id / 100,
        convergence=len(pubs),
        contributing_sources=pubs,
        # `pubs` is what backs THIS item, so it is both the driver's graph evidence and the item's
        # own coverage. The published count reads the latter (task 016): the claim must move when
        # membership does, and `contributing_sources` is graph-wide and cannot.
        coverage_sources=pubs,
        driver=driver,
        driver_uid=driver_uid,
    )


# ---- membership: a shared driver is required ----


def test_mixed_drivers_do_not_converge():
    """Three items that each converge — on three DIFFERENT entities — are a list, not a cluster."""
    items = [
        _converger(1, driver="Alpha", driver_uid=101, pubs=("VentureBeat", "The Register")),
        _converger(2, driver="Beta", driver_uid=102, pubs=("arXiv", "Hacker News")),
        _converger(3, driver="Gamma", driver_uid=103, pubs=("The Register", "MIT TR")),
    ]
    assert all(it.convergence > 0 for it in items)      # the old per-item filter would take all 3
    assert coherent_cluster(items, min_items=2) == ((), "")

    data = _sections(items)
    assert data.weak_driver == ""
    _cluster, converged = weak_cluster(data)
    assert converged is False

    bundle = generate_posts(data)
    assert bundle.has_convergence is False
    for surface in _WEAK_SURFACES:
        text = _one(bundle, surface).text.lower()
        assert "converging" not in text, f"{surface} claims convergence over unrelated drivers"
        assert "independent sources" not in text, f"{surface} claims a shared source count"


def test_shared_driver_converges():
    """Items on the SAME driving entity are a real cluster, labelled with the entity."""
    items = [
        _converger(1, driver=DRIVER, driver_uid=DRIVER_UID, pubs=_PUBS),
        _converger(2, driver=DRIVER, driver_uid=DRIVER_UID, pubs=_PUBS),
        _converger(3, driver=DRIVER, driver_uid=DRIVER_UID, pubs=_PUBS),
        _converger(4, driver="Unrelated", driver_uid=999, pubs=("MIT TR", "Hacker News", "arXiv")),
    ]
    cluster, driver = coherent_cluster(items, min_items=2)
    assert driver == DRIVER
    assert {it.event_id for it in cluster} == {1, 2, 3}  # the off-driver item is not a member

    data = _sections(items)
    assert data.weak_driver == DRIVER
    selected, converged = weak_cluster(data)
    assert converged is True
    assert {it.event_id for it in selected} == {1, 2, 3}

    bundle = generate_posts(data)
    assert bundle.has_convergence is True
    linkedin = _one(bundle, SURFACE_LINKEDIN)
    assert DRIVER in linkedin.hook and "converging" in linkedin.hook
    assert DRIVER in _one(bundle, SURFACE_MEDIUM).text


def test_cluster_label_is_entity_not_headline():
    """The M7.5 regression: the cluster was labelled with `items[0].title`, one publisher's framing."""
    data = converging_digest()
    lead_title = data.weak_signals[0].title
    bundle = generate_posts(data)

    medium = _one(bundle, SURFACE_MEDIUM)
    assert medium.hook == f"Weak Signal of the Week: {DRIVER}"
    assert lead_title not in medium.hook

    for surface in (SURFACE_X, SURFACE_LINKEDIN):
        hook = _one(bundle, surface).hook
        assert DRIVER in hook, f"{surface} hook is not labelled with the driving entity"
        assert lead_title not in hook, f"{surface} hook still uses the lead item's headline"


def test_publisher_count_scoped_to_driver():
    """"N independent sources" must be N sources behind ONE claim, not a union across items."""
    on_driver = (
        _converger(1, driver=DRIVER, driver_uid=DRIVER_UID, pubs=("VentureBeat", "The Register")),
        _converger(2, driver=DRIVER, driver_uid=DRIVER_UID, pubs=("VentureBeat", "The Register")),
    )
    # An off-driver item smuggled into the rendered cluster: its three publishers back a DIFFERENT
    # claim and must not be counted (this union is exactly what inflated "9 independent sources").
    off_driver = _converger(3, driver="Unrelated", driver_uid=999,
                            pubs=("MIT TR", "Hacker News", "LinkFarm"))
    data = DigestData(
        period_start=None, period_end=None, total_events=3, item_count=3, noise_count=0,
        graphrag=True, weak_signals=(*on_driver, off_driver), referenced_event_ids=(1, 2, 3),
        noise=(), weak_driver=DRIVER, **_empty_sections(),
    )

    bundle = generate_posts(data)
    assert bundle.has_convergence is True
    for surface in (SURFACE_X, SURFACE_LINKEDIN):
        text = _one(bundle, surface).text
        assert "2 independent sources" in text, f"{surface} lost the driver-scoped source count"
        assert "5 independent sources" not in text, f"{surface} unioned unrelated publishers"
    medium = _one(bundle, SURFACE_MEDIUM).text
    assert "**2 independent publishers**" in medium
    assert "MIT TR" not in medium.split("## The cluster")[0], "off-driver publisher credited"
    # URL invariant: the off-driver item is still linked, it just does not back the claim.
    for it in (*on_driver, off_driver):
        assert it.source_url in medium


# ---- honest degradation ----


def test_no_cluster_degrades_honestly():
    """No coherent cluster is a valid, shippable result — quiet-week framing, no claim, URLs kept."""
    bundle = generate_posts(thin_digest())
    assert bundle.has_convergence is False
    for surface in _WEAK_SURFACES:
        draft = _one(bundle, surface)
        low = draft.text.lower()
        assert "converging" not in low, f"{surface} makes a converging claim on a quiet week"
        assert "quiet" in low, f"{surface} is missing the honest quiet-week framing"
        assert draft.source_urls
        for url in draft.source_urls:
            assert url in draft.text, f"{surface} dropped a source URL on the degraded path"


# ---- D-016 ruling D: an archive-tier signal is permitted, an undisclosed one is not ----


def test_archive_tier_cluster_is_disclosed():
    """A cluster built from `archive` items must say so and claim no top-tier provenance."""
    items = [
        _converger(i, driver=DRIVER, driver_uid=DRIVER_UID, pubs=_PUBS, priority_class="archive")
        for i in (1, 2, 3)
    ]
    data = _sections(items)
    assert data.weak_driver == DRIVER              # archive is in HORIZON_CLASSES; it still clusters

    bundle = generate_posts(data)
    assert bundle.has_convergence is True
    for surface in _WEAK_SURFACES:
        text = _one(bundle, surface).text
        assert "archive-tier" in text, f"{surface} hides the tier the cluster was drawn from"
        assert "No top-tier provenance is claimed." in text, f"{surface} omits the disclaimer"

    # The disclosure only appears when it is TRUE — a horizon-signal cluster carries no such line.
    horizon = generate_posts(_sections([
        _converger(i, driver=DRIVER, driver_uid=DRIVER_UID, pubs=_PUBS) for i in (4, 5, 6)
    ]))
    for surface in _WEAK_SURFACES:
        assert "archive-tier" not in _one(horizon, surface).text


def test_noise_items_are_unaffected_by_cluster_grouping():
    """Guard: grouping changes the weak-signal cluster only — the Noise Report is untouched."""
    data = converging_digest()
    noise_urls = {it.source_url for it in _noise_items()}
    medium = _one(generate_posts(data), SURFACE_MEDIUM, piece=PIECE_NOISE_REPORT)
    for url in noise_urls:
        assert url in medium.text
