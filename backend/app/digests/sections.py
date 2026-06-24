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

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session, select

from app.api import dashboard_service
from app.models import EnrichedItem, RawItem
from app.scoring.graph_signals import GraphSignal
from app.scoring.ranking import rank_with_graph, salience

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


def build_sections(
    items: list[DigestItem],
    signals: Mapping[int, GraphSignal],
    *,
    high_hype: int,
    section_limit: int,
    graphrag: bool,
    period_start: datetime | None,
    period_end: datetime | None,
) -> DigestData:
    """Route the period's DigestItems into the ten sections (pure)."""
    noise = [it for it in items if is_noise(it, high_hype=high_hype)]
    body = [it for it in items if not is_noise(it, high_hype=high_hype)]

    must_know = _rank([it for it in body if it.priority_class == "immediate_priority"],
                      signals, section_limit)
    should_read = _rank([it for it in body if it.priority_class == "operational_update"],
                        signals, section_limit)

    # Weak signals: the horizon quadrant. Prefer the genuinely converging ones — `convergence > 0`
    # is set only when the hub-dampened contribution fires (>= GRAPH_MIN_SOURCES distinct sources),
    # so it excludes items that merely have a recency nudge. If none converged (or Neo4j is down),
    # fall back to the whole quadrant by hype-aware salience.
    quadrant = [it for it in items if it.priority_class in HORIZON_CLASSES]
    converging = [it for it in quadrant if it.convergence > 0]
    weak_signals = _rank_weak(converging or quadrant, section_limit)

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
    )


def _dedup(items: list[DigestItem]) -> list[DigestItem]:
    seen: set[int] = set()
    out: list[DigestItem] = []
    for it in items:
        if it.event_id not in seen:
            seen.add(it.event_id)
            out.append(it)
    return out
