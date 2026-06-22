"""Shared read logic behind /items, /graph, /horizon (M6).

Pulls enriched Events out of SQLite, computes the graph signal (when a store is available), and
serialises to the API shapes. Ranking reuses `scoring.ranking.rank_with_graph` and
`scoring.graph_signals` — the priority class still comes only from the canonical rule, and hype
still demotes. Nothing here re-derives scoring.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.graph import GraphStore
from app.models import EnrichedItem, Entity, Feedback, RawItem, Relationship
from app.schemas.api import HorizonItemOut, ItemOut, ScoresOut
from app.schemas.enrichment import normalise_entity_name
from app.scoring import feedback as feedback_scoring
from app.scoring import graph_signals
from app.scoring.feedback import FeedbackState
from app.scoring.graph_signals import GraphSignal
from app.scoring.ranking import rank_with_graph, salience

# The "weak-signal quadrant": the low-relevance items a class-first feed buries.
HORIZON_CLASSES = ("horizon_signal", "archive")


def _event_ids_for_entity(session: Session, entity_name: str) -> set[int]:
    """Event ids whose relationships reference an entity matching `entity_name` (normalised)."""
    normalised = normalise_entity_name(entity_name)
    entity_ids = [
        e.id for e in session.exec(
            select(Entity).where(Entity.normalised_name == normalised)
        ).all()
    ]
    if not entity_ids:
        return set()
    rels = session.exec(
        select(Relationship).where(
            (Relationship.subject_entity_id.in_(entity_ids))
            | (Relationship.object_entity_id.in_(entity_ids))
        )
    ).all()
    return {r.event_id for r in rels if r.event_id is not None}


def load_enriched(
    session: Session,
    *,
    priority_class: str | None = None,
    priority_classes: tuple[str, ...] | None = None,
    entity: str | None = None,
) -> list[EnrichedItem]:
    """Load enriched items, optionally filtered by priority class(es) and/or mentioned entity."""
    rows = session.exec(select(EnrichedItem)).all()
    if priority_class is not None:
        rows = [r for r in rows if r.priority_class == priority_class]
    if priority_classes is not None:
        allowed = set(priority_classes)
        rows = [r for r in rows if r.priority_class in allowed]
    if entity:
        event_ids = _event_ids_for_entity(session, entity)
        rows = [r for r in rows if r.event_id in event_ids]
    return rows


def compute_signals(
    session: Session, store: GraphStore | None, rows: list[EnrichedItem]
) -> dict[int, GraphSignal]:
    """Graph signal per event id, or empty (degrade) when no store is available."""
    if store is None or not rows:
        return {}
    return graph_signals.compute_signals(session, store, [r.event_id for r in rows])


def load_feedback_states(session: Session) -> dict[int, FeedbackState]:
    """The latest-wins feedback state per Event (M7) — empty before any feedback exists."""
    return feedback_scoring.latest_feedback(session.exec(select(Feedback)).all())


def _representative(session: Session, enriched: EnrichedItem) -> RawItem | None:
    if enriched.raw_item_id is not None:
        item = session.get(RawItem, enriched.raw_item_id)
        if item is not None:
            return item
    return session.exec(
        select(RawItem).where(RawItem.event_id == enriched.event_id).order_by(RawItem.id)
    ).first()


def serialize_item(
    session: Session, enriched: EnrichedItem, signal: GraphSignal | None
) -> ItemOut:
    item = _representative(session, enriched)
    title = item.title if item is not None else "(untitled)"
    source_name = item.source_name if item is not None else ""
    published = item.published_at.isoformat() if (item and item.published_at) else None
    return ItemOut(
        id=str(enriched.event_id),
        title=title,
        source_name=source_name,
        source_url=enriched.source_url,
        published_at=published,
        priority_class=enriched.priority_class,
        category=enriched.category,
        tags=list(enriched.tags or []),
        scores=ScoresOut(
            relevance=enriched.relevance,
            novelty=enriched.novelty,
            actionability=enriched.actionability,
            strategic_potential=enriched.strategic_potential,
            hype=enriched.hype,
        ),
        summary=enriched.summary,
        why_it_matters=enriched.why_it_matters,
        recommended_action=enriched.recommended_action,
        is_weak_signal=enriched.is_weak_signal,
        horizon=enriched.horizon,
        graph_why=signal.why if signal else "",
        convergence=signal.convergence if signal else 0,
    )


def ranked_items(
    session: Session,
    store: GraphStore | None,
    *,
    priority_class: str | None = None,
    entity: str | None = None,
    limit: int = 100,
    include_ignored: bool = False,
) -> list[ItemOut]:
    """Core Radar order: priority class first, then hype-aware salience + graph + feedback (M5/M7).

    Feedback folds in transparently: `ignore`d Events drop from this default feed (unless
    `include_ignored`), useful/save lift and not_useful demotes within the class. The priority class
    is never changed and hype still demotes.
    """
    rows = load_enriched(session, priority_class=priority_class, entity=entity)
    states = load_feedback_states(session)
    if not include_ignored:
        hidden = feedback_scoring.hidden_event_ids(states)
        rows = [r for r in rows if r.event_id not in hidden]
    signals = compute_signals(session, store, rows)
    deltas = feedback_scoring.feedback_deltas(states)
    ordered = rank_with_graph(rows, signals, feedback=deltas)[:limit]
    return [serialize_item(session, e, signals.get(e.event_id)) for e in ordered]


def _event_coverage_sources(session: Session, event_id: int) -> list[str]:
    """Distinct source names of the items grouped into this Event (its independent coverage)."""
    items = session.exec(select(RawItem).where(RawItem.event_id == event_id)).all()
    seen: list[str] = []
    for it in items:
        if it.source_name and it.source_name not in seen:
            seen.append(it.source_name)
    return seen


def _contributing_sources(
    session: Session, event_id: int, signal: GraphSignal | None
) -> list[str]:
    """The evidence behind the card's `why` (M5.5).

    When the graph signal fired, the evidence is the **driving entity's** distinct sources — so the
    card's claim ("convergence: 'X' across N sources") and the listed sources agree (M6 finding #3).
    Otherwise (no signal / Neo4j down) fall back to this Event's own coverage sources.
    """
    if signal is not None and signal.evidence_sources:
        return list(signal.evidence_sources)
    return _event_coverage_sources(session, event_id)


def horizon_items(
    session: Session, store: GraphStore | None, *, limit: int = 50
) -> list[HorizonItemOut]:
    """The weak-signal quadrant ranked by graph convergence (NOT the Core Radar order).

    Selects horizon_signal/archive items — the low-relevance ones the class-first feed buries — and
    ranks THEM by the (hub-dampened) graph signal, so a quietly-converging item rises to the top.
    Each carries its `why` and the contributing sources behind that `why`. Degrades when Neo4j is
    down.
    """
    rows = load_enriched(session, priority_classes=HORIZON_CLASSES)
    signals = compute_signals(session, store, rows)

    def sort_key(e: EnrichedItem) -> tuple[float, float]:
        sig = signals.get(e.event_id)
        score = sig.score if sig else 0.0
        return (-score, -salience(e))  # convergence first, then hype-aware salience

    ordered = sorted(rows, key=sort_key)[:limit]
    out: list[HorizonItemOut] = []
    for e in ordered:
        sig = signals.get(e.event_id)
        base = serialize_item(session, e, sig)
        out.append(HorizonItemOut(
            **base.model_dump(),
            graph_score=sig.score if sig else 0.0,
            contributing_sources=_contributing_sources(session, e.event_id, sig),
        ))
    return out
