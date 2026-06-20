"""Graph-aware ranking signal (M5) — convergence + centrality + recency.

A **transparent, documented adjustment** computed from the Neo4j graph and layered ON TOP OF the
canonical priority class. It reorders items *within/across* classes; it never changes the priority
class (that stays `compute_priority_class`) and never lifts a high-hype item (hype stays a demotion
in `scoring/ranking.salience`).

The headline signal is **convergence** (SIGNATURE_OUTPUTS §1): the number of *distinct sources*
touching the same entity within a window — many individually-weak indicators pointing the same way.
Secondary signals are **degree/centrality** (how connected the entity is) and **recency** (how fresh
the activity is). Each is weighted and summed into one `score`, with a human-readable `why`.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
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
    """The graph adjustment for one Event, plus a `why` naming the signal that fired."""

    convergence: int = 0          # max distinct sources on a mentioned entity
    degree: int = 0               # max centrality (incident interactions) of a mentioned entity
    recency_days: float | None = None  # age (days) of the most recent mention
    score: float = 0.0            # the combined adjustment (>= 0)
    why: str = ""                 # e.g. "convergence: 'RAG' across 6 sources"

    @property
    def is_signal(self) -> bool:
        return self.score > 0.0


_ZERO = GraphSignal()


def _event_entity_ids(session: Session, event_id: int) -> set[int]:
    rels = session.exec(select(Relationship).where(Relationship.event_id == event_id)).all()
    return {r.subject_entity_id for r in rels} | {r.object_entity_id for r in rels}


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
) -> dict[int, GraphSignal]:
    """Return a `GraphSignal` per event id, computed from the graph's convergence read.

    Configurable via `settings.*` (overridable per-arg). Pure read — needs no live Neo4j when the
    `store` is the in-memory graph.
    """
    now = now or datetime.now(timezone.utc)
    window_days = settings.convergence_window_days if window_days is None else window_days
    w_conv = settings.graph_convergence_weight if convergence_weight is None else convergence_weight
    w_deg = settings.graph_degree_weight if degree_weight is None else degree_weight
    w_rec = settings.graph_recency_weight if recency_weight is None else recency_weight

    since = None
    if window_days and window_days > 0:
        since = now - timedelta(days=window_days)

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

        # The driving entity: most distinct sources, then degree, then recency.
        driver = max(relevant, key=lambda s: (s.distinct_sources, s.degree, s.last_ts or _MIN))
        convergence = max(s.distinct_sources for s in relevant)
        degree = max(s.degree for s in relevant)
        last_ts = max((to_utc(s.last_ts) for s in relevant if s.last_ts), default=None)

        recency_days: float | None = None
        recency_factor = 0.0
        if last_ts is not None:
            recency_days = max(0.0, (now - last_ts).total_seconds() / 86400.0)
            if window_days and window_days > 0:
                recency_factor = max(0.0, 1.0 - recency_days / window_days)
            else:
                recency_factor = 1.0  # no window → treat any dated activity as "present"

        score = (
            w_conv * convergence
            + w_deg * math.log1p(degree)
            + w_rec * recency_factor
        )

        out[event_id] = GraphSignal(
            convergence=convergence,
            degree=degree,
            recency_days=recency_days,
            score=score,
            why=_why(session, driver, convergence, degree, recency_factor),
        )
    return out


def _why(session: Session, driver: ConvergenceStat, convergence: int, degree: int,
         recency_factor: float) -> str:
    name = _entity_name(session, driver.entity_uid)
    parts: list[str] = []
    if convergence >= 2:
        parts.append(f"convergence: '{name}' across {convergence} sources")
    if degree >= 2:
        parts.append(f"central: '{name}' degree {degree}")
    if recency_factor >= 0.5:
        parts.append("recent activity")
    return "; ".join(parts)


def _entity_name(session: Session, entity_id: int) -> str:
    entity = session.get(Entity, entity_id)
    return entity.name if entity is not None else f"#{entity_id}"
