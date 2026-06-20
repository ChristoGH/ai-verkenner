"""Graph-aware ranking signal — convergence + centrality + recency, with hub-dampening (M5.5).

A **transparent, documented adjustment** computed from the Neo4j graph and layered ON TOP OF the
canonical priority class. It reorders items *within/across* classes; it never changes the priority
class (that stays `compute_priority_class`) and never lifts a high-hype item (hype stays a demotion
in `scoring/ranking.salience`).

The headline signal is **convergence** (SIGNATURE_OUTPUTS §1): an entity that *quietly* emerges
across multiple independent sources and multiple developments. The M6 real-data smoke
(`docs/m6-smoke-notes.md`) showed the naive "distinct sources" version instead rewarded ubiquitous
**hubs** ('GitHub', a prolific author) — "loud everywhere," the opposite of "emerging." M5.5 fixes
that with three documented dampeners:

1. **Independence gate.** An entity must be touched by ≥ `GRAPH_MIN_SOURCES` (default 2) *distinct*
   sources to count — a single prolific feed/author mentioning an entity many times is **not**
   convergence. The centrality (degree) term is gated by the same rule, so a single-feed author hub
   can't dominate via its connections either.
2. **IDF weighting.** Convergence is weighted by inverse document frequency
   `idf = ln(total_developments / developments_mentioning_entity)`: a hub mentioned in almost every
   event is suppressed; a rare entity converging is amplified.
3. **Singleton suppression.** An entity confined to a single development (event) contributes ~0 —
   that's ordinary coverage, not an emerging *cross-development* cluster (and it stops IDF from
   inflating hyper-specific one-off concepts).

The driving entity is the one with the largest *dampened* contribution, and the `why` evidence (its
distinct sources) is returned so the card's claim and its listed sources agree.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.core.config import settings
from app.graph.store import ConvergenceStat, GraphStore
from app.graph.util import to_utc
from app.models import Entity, Relationship

logger = logging.getLogger(__name__)

# A floor for "no timestamp" when picking the most-recent driving entity.
_MIN = datetime.min.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class GraphSignal:
    """The graph adjustment for one Event, plus the evidence behind it."""

    convergence: int = 0          # distinct INDEPENDENT sources on the driving entity (0 if none)
    degree: int = 0               # centrality of the driving entity
    recency_days: float | None = None  # age (days) of the most recent mention
    score: float = 0.0            # the combined (dampened) adjustment (>= 0)
    why: str = ""                 # e.g. "convergence: 'X' across 3 independent sources ..."
    driver: str = ""              # the driving entity name (the convergence is about)
    evidence_sources: tuple[str, ...] = field(default_factory=tuple)  # driver's distinct sources
    event_count: int = 0          # developments the driving entity spans (breadth)
    idf: float = 0.0              # rarity weight that made it win (for transparency)

    @property
    def is_signal(self) -> bool:
        return self.score > 0.0


_ZERO = GraphSignal()


def _event_entity_ids(session: Session, event_id: int) -> set[int]:
    rels = session.exec(select(Relationship).where(Relationship.event_id == event_id)).all()
    return {r.subject_entity_id for r in rels} | {r.object_entity_id for r in rels}


def _total_developments(session: Session) -> int:
    """Distinct events that carry any extracted relationship — the IDF denominator (>= 1)."""
    ids = session.exec(select(Relationship.event_id)).all()
    return max(len({e for e in ids if e is not None}), 1)


def _contribution(
    stat: ConvergenceStat, total_developments: int, min_sources: int,
    w_conv: float, w_deg: float,
) -> tuple[float, float]:
    """The dampened convergence+centrality contribution of one entity, and the IDF used.

    Returns 0 for anything that is not genuine cross-source, cross-development convergence:
    the independence gate (< `min_sources` distinct sources) and singleton suppression
    (< 2 developments) both floor it to zero.
    """
    if stat.distinct_sources < min_sources:
        return 0.0, 0.0
    if stat.event_count < 2:
        return 0.0, 0.0
    idf = math.log(total_developments / stat.event_count)
    if idf <= 0.0:
        return 0.0, 0.0  # the entity spans (nearly) every development → a hub, not a signal
    conv_term = w_conv * stat.distinct_sources * idf
    degree_term = w_deg * math.log1p(stat.degree) * idf
    return conv_term + degree_term, idf


def compute_signals(
    session: Session,
    store: GraphStore,
    event_ids: list[int],
    *,
    now: datetime | None = None,
    window_days: int | None = None,
    convergence_weight: float | None = None,
    degree_weight: float | None = None,
    recency_weight: float | None = None,
    min_sources: int | None = None,
) -> dict[int, GraphSignal]:
    """Return a `GraphSignal` per event id from the graph's convergence read (hub-dampened).

    Configurable via `settings.*` (overridable per-arg). Pure read — needs no live Neo4j when the
    `store` is the in-memory graph.
    """
    now = now or datetime.now(timezone.utc)
    window_days = settings.convergence_window_days if window_days is None else window_days
    w_conv = settings.graph_convergence_weight if convergence_weight is None else convergence_weight
    w_deg = settings.graph_degree_weight if degree_weight is None else degree_weight
    w_rec = settings.graph_recency_weight if recency_weight is None else recency_weight
    min_sources = settings.graph_min_sources if min_sources is None else min_sources

    since = None
    if window_days and window_days > 0:
        since = now - timedelta(days=window_days)

    total_developments = _total_developments(session)
    stats_by_uid: dict[int, ConvergenceStat] = {
        st.entity_uid: st for st in store.convergence(since)
    }

    out: dict[int, GraphSignal] = {}
    for event_id in event_ids:
        entity_ids = _event_entity_ids(session, event_id)
        relevant = [stats_by_uid[eid] for eid in entity_ids if eid in stats_by_uid]
        if not relevant:
            out[event_id] = _ZERO
            continue

        # The driving entity maximises the DAMPENED contribution — so a rare cross-source entity
        # wins over a ubiquitous hub even if the hub has more raw sources.
        scored = [(stat, *_contribution(stat, total_developments, min_sources, w_conv, w_deg))
                  for stat in relevant]
        driver_stat, driver_contrib, driver_idf = max(
            scored, key=lambda t: (t[1], t[0].distinct_sources, t[0].last_ts or _MIN)
        )

        # Recency (a small, ungated tiebreak) from the most-recent mention among the entities.
        last_ts = max((to_utc(s.last_ts) for s in relevant if s.last_ts), default=None)
        recency_days: float | None = None
        recency_factor = 0.0
        if last_ts is not None:
            recency_days = max(0.0, (now - last_ts).total_seconds() / 86400.0)
            recency_factor = (
                max(0.0, 1.0 - recency_days / window_days)
                if (window_days and window_days > 0)
                else 1.0
            )

        score = driver_contrib + w_rec * recency_factor

        if driver_contrib > 0.0:
            driver_name = _entity_name(session, driver_stat.entity_uid)
            out[event_id] = GraphSignal(
                convergence=driver_stat.distinct_sources,
                degree=driver_stat.degree,
                recency_days=recency_days,
                score=score,
                why=_why(driver_name, driver_stat, recency_factor),
                driver=driver_name,
                evidence_sources=driver_stat.source_names,
                event_count=driver_stat.event_count,
                idf=driver_idf,
            )
        else:
            # No genuine convergence — only a tiny recency tiebreak, no claim to surface.
            out[event_id] = GraphSignal(score=score, recency_days=recency_days)
    return out


def _why(driver_name: str, stat: ConvergenceStat, recency_factor: float) -> str:
    parts = [
        f"convergence: '{driver_name}' across {stat.distinct_sources} independent sources "
        f"in {stat.event_count} developments"
    ]
    if recency_factor >= 0.5:
        parts.append("recent activity")
    return "; ".join(parts)


def _entity_name(session: Session, entity_id: int) -> str:
    entity = session.get(Entity, entity_id)
    return entity.name if entity is not None else f"#{entity_id}"
