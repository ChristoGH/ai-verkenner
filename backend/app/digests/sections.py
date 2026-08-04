"""Digest section routing (M7) — pure logic over already-enriched Events.

Turns the period's enriched Events into the ten decision-oriented sections of `prompts/digest.md`.
This module **does not re-derive ranking or the priority rule**: it reuses
`scoring.ranking.rank_with_graph` (priority class first, then hype-aware salience + graph signal) to
order the list sections, and `scoring.ranking.salience` for the weak-signal tiebreak. Section
membership is grounded in *source facts* — the canonical `priority_class`, the item's `source_type`,
and its category/tags — so it is deterministic and testable offline.

Polarity honoured throughout: the four salient axes lift; `hype` is inverted and only ever demotes
(an item is "noise" when it is `archive` or `hype >= high_hype`).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session, select

from app.api import dashboard_service
from app.models import EnrichedItem, RawItem
from app.schemas.enrichment import normalise_entity_name
from app.scoring.graph_signals import GraphSignal
from app.scoring.ranking import rank_with_graph, salience

logger = logging.getLogger(__name__)

# The weak-signal quadrant (matches /horizon): the low-relevance items the class-first feed buries.
HORIZON_CLASSES = ("horizon_signal", "archive")

# The ten sections of the digest, in order. Length-10 is asserted by the tests and the render.
SECTION_HEADINGS: tuple[str, ...] = (
    "Executive summary",
    "Must-know",
    "Should-read",
    "Weak signals",
    "Research radar",
    "Tool changes",
    "Risks",
    "Opportunities",
    "Suggested experiments",
    "Ignored / noise count",
)

# Source-fact routing hints (grounded in the curated source_type + the enrichment category/tags).
_RESEARCH_TYPES = {"arxiv"}
_RESEARCH_KW = {"research", "paper", "preprint"}
_TOOL_TYPES = {"github_releases"}
_TOOL_KW = {"release", "tool", "framework", "library", "update", "changelog"}
_RISK_TYPES = {"github_advisories", "github_changes"}
_RISK_KW = {"security", "advisory", "vulnerability", "deprecation", "breaking", "cve", "exploit"}


@dataclass(frozen=True)
class DigestItem:
    """One Event flattened for the digest. Carries the score attributes so `salience` / ranking work.

    Source fact (`summary`) stays separate from interpretation (`why_it_matters`,
    `recommended_action`); the `source_url` is always preserved.
    """

    event_id: int
    title: str
    source_name: str
    source_url: str
    source_type: str
    published_at: datetime | None
    priority_class: str
    category: str
    tags: tuple[str, ...]
    relevance: int
    novelty: int
    actionability: int
    strategic_potential: int
    hype: int
    summary: str
    why_it_matters: str
    connection_to_user_work: str
    recommended_action: str
    is_weak_signal: bool
    horizon: str | None
    graph_why: str
    graph_score: float
    convergence: int
    contributing_sources: tuple[str, ...]
    # The driving entity behind this item's convergence (`GraphSignal.driver`). `driver_uid` is the
    # normalised identity and the ONLY grouping key — the display name is never grouped on.
    driver: str = ""
    driver_uid: int | None = None
    # The driving entity's ambient corpus volume over the convergence window (`GraphSignal.
    # driver_mentions`). The quietness ordering in `coherent_cluster` keys off it (task 013).
    driver_mentions: int = 0


@dataclass(frozen=True)
class DigestData:
    """The structured digest — the deterministic backbone behind both renders."""

    period_start: datetime | None
    period_end: datetime | None
    total_events: int          # the universe summarised (the period corpus)
    item_count: int            # non-noise Events considered for the body
    noise_count: int           # archived / high-hype Events excluded (the honest count)
    graphrag: bool             # whether Qdrant-retrieve / Neo4j-expand actually ran
    must_know: tuple[DigestItem, ...]
    should_read: tuple[DigestItem, ...]
    weak_signals: tuple[DigestItem, ...]
    research_radar: tuple[DigestItem, ...]
    tool_changes: tuple[DigestItem, ...]
    risks: tuple[DigestItem, ...]
    opportunities: tuple[DigestItem, ...]
    suggested_experiments: tuple[DigestItem, ...]
    referenced_event_ids: tuple[int, ...]
    # The actual demoted items behind `noise_count` — archived / high-hype (loudest-but-emptiest).
    # Kept so the M7.5 Noise Report can name them, not just count them. Same `is_noise` predicate,
    # same hype polarity — not a ranking change.
    noise: tuple[DigestItem, ...]
    # The driving entity NAME shared by every item in `weak_signals`, when a coherent cluster was
    # found (see `coherent_cluster`). Empty string = no coherent cluster; `weak_signals` is then the
    # quiet-week quadrant and NO convergence may be claimed about it.
    weak_driver: str = ""


def _representative(session: Session, enriched: EnrichedItem) -> RawItem | None:
    if enriched.raw_item_id is not None:
        item = session.get(RawItem, enriched.raw_item_id)
        if item is not None:
            return item
    return session.exec(
        select(RawItem).where(RawItem.event_id == enriched.event_id).order_by(RawItem.id)
    ).first()


def build_items(
    session: Session, rows: list[EnrichedItem], signals: Mapping[int, GraphSignal]
) -> list[DigestItem]:
    """Flatten enriched Events (+ their graph signal) into DigestItems."""
    out: list[DigestItem] = []
    for e in rows:
        item = _representative(session, e)
        sig = signals.get(e.event_id)
        out.append(
            DigestItem(
                event_id=e.event_id,
                title=item.title if item is not None else "(untitled)",
                source_name=item.source_name if item is not None else "",
                source_url=e.source_url,
                source_type=item.source_type if item is not None else "",
                published_at=item.published_at if item is not None else None,
                priority_class=e.priority_class,
                category=e.category,
                tags=tuple(e.tags or []),
                relevance=e.relevance,
                novelty=e.novelty,
                actionability=e.actionability,
                strategic_potential=e.strategic_potential,
                hype=e.hype,
                summary=e.summary,
                why_it_matters=e.why_it_matters,
                connection_to_user_work=e.connection_to_user_work,
                recommended_action=e.recommended_action,
                is_weak_signal=e.is_weak_signal,
                horizon=e.horizon,
                graph_why=sig.why if sig else "",
                graph_score=sig.score if sig else 0.0,
                convergence=sig.convergence if sig else 0,
                contributing_sources=tuple(
                    dashboard_service._contributing_sources(session, e.event_id, sig)
                ),
                driver=sig.driver if sig else "",
                driver_uid=sig.driver_uid if sig else None,
                driver_mentions=sig.driver_mentions if sig else 0,
            )
        )
    return out


def is_noise(item: DigestItem, *, high_hype: int) -> bool:
    """Noise = the demoted quadrant: archived OR high-hype (inverted: hype >= high_hype)."""
    return item.priority_class == "archive" or item.hype >= high_hype


def _has_kw(item: DigestItem, keywords: set[str]) -> bool:
    haystack = " ".join((item.category, *item.tags)).lower()
    return any(kw in haystack for kw in keywords)


def _rank(items: list[DigestItem], signals: Mapping[int, GraphSignal], limit: int) -> tuple:
    """Order by the canonical Core-Radar key (priority class, then salience + graph) and cap."""
    return tuple(rank_with_graph(items, signals)[:limit])


def _rank_weak(items: list[DigestItem], limit: int) -> tuple:
    """Weak-signal order: graph convergence first, then hype-aware salience (mirrors /horizon)."""
    return tuple(sorted(items, key=lambda it: (-it.graph_score, -salience(it)))[:limit])


def _ambient_mentions(group: list[DigestItem]) -> int:
    """The driver's total corpus mentions over the convergence window.

    Every member of a group shares one `driver_uid`, so every member carries the same figure from
    the same `ConvergenceStat`; `max` only keeps the value defined for hand-built items.
    """
    return max(it.driver_mentions for it in group)


def _driver_sources(group: list[DigestItem]) -> int:
    """Distinct independent sources behind the group's shared driver.

    `DigestItem.convergence` *is* that count (`GraphSignal.convergence` = the driving entity's
    `distinct_sources`), and every member of a group shares one driver, so they all carry the same
    figure; `max` only guards hand-built items.
    """
    return max(it.convergence for it in group)


def _eligible_driver(name: str, blocked: set[str]) -> bool:
    """A driver may label a weak signal unless it is a stoplisted generic concept (task 013 B).

    Matched on the *normalised* identity — the same lower/trim/collapse rule entity resolution uses
    — so "LLMs", "llms " and "LLMs" are one term. An unnamed driver is also ineligible: a cluster
    labelled with an empty string can carry no claim.
    """
    normalised = normalise_entity_name(name)
    return bool(normalised) and normalised not in blocked


def coherent_cluster(
    items: list[DigestItem], *, min_items: int, min_sources: int | None = None,
    stoplist: Iterable[str] | None = None,
) -> tuple[tuple[DigestItem, ...], str]:
    """The **quietest eligible** group of items converging on one shared driving entity, + its name.

    Two rules, in order:

    1. **Membership** (task 010 / D-019). `convergence > 0` is a **per-item** property: *this* item's
       own driver crossed `>= GRAPH_MIN_SOURCES` distinct sources. Filtering on it alone collects
       items that each converge on a *different, unrelated* entity and presents them as one cluster
       — the M7.5 defect. Membership therefore requires a shared `driver_uid`: the normalised entity
       identity, never the display name. The `>= GRAPH_MIN_SOURCES` rule is already carried by
       `convergence > 0` (the contribution is floored to zero below it in `scoring.graph_signals`),
       so it is inherited here, not re-derived.

    2. **Selection** (task 013 / D-026, D-047). Among the groups that clear the corroboration bar,
       the winner is the driver with the **lowest ambient mention count** — a weak signal is
       *corroborated but not yet loud*, so "largest group wins" optimised for the inverse of the
       definition and structurally selected the corpus's loudest entity (D-024: OpenAI, "quietly
       converging"). Ties break: lower mentions → larger group → higher summed graph score → lower
       uid, so selection is deterministic.

       The bar is three separate filters: `len(group) >= min_items`, `>= min_sources` distinct
       sources on the driver, and a driver that is not a stoplisted generic concept. The two numeric
       floors exist **because** the objective is a minimiser: it lands on whatever the floor allows,
       so a floor of 2 makes "2 mentions / 2 sources / 2 items" the winner by construction — which
       is coincidence, not corroboration (D-047, the `Firefox` fixed point). These floors are
       **selection-only** and deliberately higher than `GRAPH_MIN_SOURCES`, which stays where it is.

    No convergence maths is touched here: this decides *which* group is chosen, not how convergence
    is computed. Returns `((), "")` when no eligible group survives — the honest "quiet week"
    answer, which is a correct outcome and never something to widen eligibility to avoid.
    """
    from app.core.config import settings

    if stoplist is None:
        stoplist = settings.weak_driver_stoplist
    if min_sources is None:
        min_sources = settings.weak_driver_min_sources
    blocked = {normalise_entity_name(name) for name in stoplist}

    groups: dict[int, list[DigestItem]] = {}
    for it in items:
        if it.convergence > 0 and it.driver_uid is not None:
            groups.setdefault(it.driver_uid, []).append(it)

    eligible = {
        uid: group
        for uid, group in groups.items()
        if len(group) >= min_items
        and _driver_sources(group) >= min_sources
        and _eligible_driver(group[0].driver, blocked)
    }
    if not eligible:
        logger.info(
            "weak signal: no eligible driver — %d shared-driver group(s), min_items=%d, "
            "min_sources=%d, %d stoplisted term(s) applied",
            len(groups), min_items, min_sources, len(blocked),
        )
        return (), ""

    uid, best = min(
        eligible.items(),
        key=lambda kv: (
            _ambient_mentions(kv[1]),
            -len(kv[1]),
            -sum(it.graph_score for it in kv[1]),
            kv[0],
        ),
    )
    # Auditability: the chosen driver's stats, so the "quietest" claim can be checked against the
    # corpus without re-running the selection.
    logger.info(
        "weak signal driver: %r (uid=%s) — mentions=%d, distinct sources=%d, group size=%d; "
        "quietest of %d eligible group(s) out of %d shared-driver group(s) "
        "(floor: min_items=%d, min_sources=%d)",
        best[0].driver, uid, _ambient_mentions(best), _driver_sources(best),
        len(best), len(eligible), len(groups), min_items, min_sources,
    )
    return tuple(best), best[0].driver


def build_sections(
    items: list[DigestItem],
    signals: Mapping[int, GraphSignal],
    *,
    high_hype: int,
    section_limit: int,
    graphrag: bool,
    period_start: datetime | None,
    period_end: datetime | None,
    weak_cluster_min_items: int | None = None,
    weak_driver_min_sources: int | None = None,
) -> DigestData:
    """Route the period's DigestItems into the ten sections (pure)."""
    from app.core.config import settings

    if weak_cluster_min_items is None:
        weak_cluster_min_items = settings.weak_cluster_min_items
    if weak_driver_min_sources is None:
        weak_driver_min_sources = settings.weak_driver_min_sources

    noise = [it for it in items if is_noise(it, high_hype=high_hype)]
    body = [it for it in items if not is_noise(it, high_hype=high_hype)]

    must_know = _rank([it for it in body if it.priority_class == "immediate_priority"],
                      signals, section_limit)
    should_read = _rank([it for it in body if it.priority_class == "operational_update"],
                        signals, section_limit)

    # Weak signals: the horizon quadrant. A convergence may be claimed only for items converging on
    # the SAME driving entity (`coherent_cluster`) — the old `convergence > 0` filter was per-item
    # and collected items converging on unrelated entities. When no coherent cluster survives (or
    # Neo4j is down), fall back to the whole quadrant by hype-aware salience and claim nothing.
    quadrant = [it for it in items if it.priority_class in HORIZON_CLASSES]
    cluster, weak_driver = coherent_cluster(
        quadrant, min_items=weak_cluster_min_items, min_sources=weak_driver_min_sources
    )
    weak_signals = _rank_weak(list(cluster) or quadrant, section_limit)

    research_radar = _rank(
        [it for it in body if it.source_type in _RESEARCH_TYPES or _has_kw(it, _RESEARCH_KW)],
        signals, section_limit,
    )
    tool_changes = _rank(
        [it for it in body if it.source_type in _TOOL_TYPES or _has_kw(it, _TOOL_KW)],
        signals, section_limit,
    )
    risks = _rank(
        [it for it in items if it.source_type in _RISK_TYPES or _has_kw(it, _RISK_KW)],
        signals, section_limit,
    )
    # Opportunities: high future value, low noise — genuine openings, not hype.
    opportunities = _rank(
        [it for it in body if it.strategic_potential >= 4 and it.hype <= 2],
        signals, section_limit,
    )
    # Suggested experiments: the most actionable must-know / tool changes carrying an action.
    experiment_pool = [it for it in (*must_know, *tool_changes) if it.recommended_action.strip()]
    suggested_experiments = _rank(_dedup(experiment_pool), signals, min(3, section_limit))

    referenced = sorted({
        it.event_id
        for section in (must_know, should_read, weak_signals, research_radar,
                        tool_changes, risks, opportunities, suggested_experiments)
        for it in section
    })

    return DigestData(
        period_start=period_start,
        period_end=period_end,
        total_events=len(items),
        item_count=len(body),
        noise_count=len(noise),
        graphrag=graphrag,
        must_know=must_know,
        should_read=should_read,
        weak_signals=weak_signals,
        research_radar=research_radar,
        tool_changes=tool_changes,
        risks=risks,
        opportunities=opportunities,
        suggested_experiments=suggested_experiments,
        referenced_event_ids=tuple(referenced),
        noise=tuple(noise),
        weak_driver=weak_driver,
    )


def _dedup(items: list[DigestItem]) -> list[DigestItem]:
    seen: set[int] = set()
    out: list[DigestItem] = []
    for it in items:
        if it.event_id not in seen:
            seen.add(it.event_id)
            out.append(it)
    return out
