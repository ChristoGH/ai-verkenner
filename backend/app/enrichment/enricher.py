"""Per-Event enrichment + extraction (M4).

Enrich once per **Event** (not per duplicate item): pick the event's representative RawItem, run
the `prompts/` templates through the injected LLM provider to produce the five scores +
summary/why/action and a structured entity/relationship payload, then persist an `EnrichedItem`
plus the graph triples to SQLite.

Invariants honoured here:
- Priority class comes **only** from `app/scoring/priority.compute_priority_class` (imported).
- hype stays inverted and is never summed with the other axes (ranking lives in scoring/ranking).
- Source fact (`summary`) stays separate from interpretation (`why_it_matters`, …).
- Fail-safe per item: a missing/failed/garbled LLM call degrades to the rule-based fallback.
- Idempotent: one `EnrichedItem` per Event (UNIQUE), so re-runs never re-enrich or duplicate.
"""

from __future__ import annotations

import logging

from sqlmodel import Session, select

from app.core.config import settings
from app.enrichment import prompts
from app.enrichment.fallback import fallback_enrichment
from app.enrichment.graph_store import persist_graph
from app.enrichment.parse import (
    parse_classify,
    parse_graph,
    parse_summarise,
    parse_weak_signal,
)
from app.enrichment.provider import LLMProvider
from app.models import EnrichedItem, Event, RawItem
from app.schemas.enrichment import (
    ClassifyResult,
    GraphExtractResult,
    SummariseResult,
    WeakSignalResult,
)
from app.scoring.priority import compute_priority_class

logger = logging.getLogger(__name__)


def representative_item(session: Session, event: Event) -> RawItem | None:
    """The item enriched for an Event: its declared representative, else the lowest-id member."""
    if event.representative_item_id is not None:
        item = session.get(RawItem, event.representative_item_id)
        if item is not None:
            return item
    return session.exec(
        select(RawItem).where(RawItem.event_id == event.id).order_by(RawItem.id)
    ).first()


class Enricher:
    """Enriches Events using an optional LLM provider, degrading to the rule-based fallback."""

    def __init__(
        self,
        provider: LLMProvider | None,
        *,
        user_context: str | None = None,
        max_entities: int | None = None,
    ) -> None:
        self.provider = provider
        self.user_context = user_context if user_context is not None else settings.user_context
        self.max_entities = (
            max_entities if max_entities is not None else settings.max_entities_per_item
        )

    # ---- LLM path (may raise; caller falls back) ----

    def _ask(self, template_name: str, item: RawItem, *, with_context: bool) -> str:
        system = prompts.load_template(template_name)
        user = prompts.render_item_inputs(
            title=item.title,
            source_name=item.source_name,
            source_url=item.url,
            published_at=item.published_at,
            content=item.summary,
            user_context=self.user_context if with_context else None,
        )
        return self.provider.complete(system=system, user=user)

    def _llm_enrich(
        self, item: RawItem
    ) -> tuple[ClassifyResult, SummariseResult, WeakSignalResult, GraphExtractResult]:
        # classify + summarise are required; if either fails we abandon the LLM path entirely.
        classify = parse_classify(self._ask(prompts.CLASSIFY, item, with_context=True))
        summarise = parse_summarise(self._ask(prompts.SUMMARISE, item, with_context=True))

        # weak-signal + graph are best-effort; a failure degrades just that part.
        try:
            weak = parse_weak_signal(self._ask(prompts.WEAK_SIGNAL, item, with_context=True))
        except Exception as exc:  # noqa: BLE001 — partial degrade, keep the rest
            logger.warning("weak-signal parse failed for item %s: %s", item.id, exc)
            weak = WeakSignalResult(is_weak_signal=False)
        try:
            graph = parse_graph(self._ask(prompts.EXTRACT_GRAPH, item, with_context=False))
        except Exception as exc:  # noqa: BLE001 — partial degrade, keep the rest
            logger.warning("graph extraction parse failed for item %s: %s", item.id, exc)
            graph = GraphExtractResult()
        return classify, summarise, weak, graph

    # ---- Public: enrich one event ----

    def enrich_event(self, session: Session, event: Event) -> EnrichedItem | None:
        """Enrich a single Event and persist its EnrichedItem + graph. Returns the row (or None)."""
        item = representative_item(session, event)
        if item is None:
            logger.warning("event %s has no items to enrich", event.id)
            return None

        method = "llm"
        if self.provider is None:
            classify, summarise, weak, graph = fallback_enrichment(item)
            method = "fallback"
        else:
            try:
                classify, summarise, weak, graph = self._llm_enrich(item)
            except Exception as exc:  # noqa: BLE001 — fail-safe per item
                logger.warning(
                    "LLM enrichment failed for event %s (item %s); using fallback: %s",
                    event.id, item.id, exc,
                )
                classify, summarise, weak, graph = fallback_enrichment(item)
                method = "fallback"

        s = classify.scores
        # The ONE source of truth for the priority class — imported, never re-derived.
        priority_class = compute_priority_class(s.relevance, s.strategic_potential)

        enriched = EnrichedItem(
            event_id=event.id,
            raw_item_id=item.id,
            source_url=item.url,  # preserved verbatim
            category=classify.category,
            tags=classify.tags,
            relevance=s.relevance,
            novelty=s.novelty,
            actionability=s.actionability,
            strategic_potential=s.strategic_potential,
            hype=s.hype,
            summary=summarise.summary,
            why_it_matters=summarise.why_it_matters,
            connection_to_user_work=summarise.connection_to_user_work,
            recommended_action=summarise.recommended_action,
            is_weak_signal=weak.is_weak_signal,
            horizon=weak.horizon,
            priority_class=priority_class,
            method=method,
        )
        session.add(enriched)
        session.commit()
        session.refresh(enriched)

        # Persist the graph triples (timestamped with the item's published time).
        ent_count, rel_count = persist_graph(
            session,
            graph,
            event_id=event.id,
            raw_item_id=item.id,
            ts=item.published_at,
            max_entities=self.max_entities,
        )
        logger.info(
            "enriched event %s via %s: class=%s entities=%d relationships=%d",
            event.id, method, priority_class, ent_count, rel_count,
        )
        return enriched


def enrich_new_events(session: Session, enricher: Enricher, new_rows: list[RawItem]) -> int:
    """Enrich the Events introduced by this run that aren't enriched yet. Returns count enriched.

    Idempotent: an Event already carrying an `EnrichedItem` is skipped (so a near-dup joining an
    already-enriched event doesn't re-enrich it, and a re-run does nothing).
    """
    event_ids: list[int] = []
    seen: set[int] = set()
    for row in new_rows:
        if row.event_id is not None and row.event_id not in seen:
            seen.add(row.event_id)
            event_ids.append(row.event_id)

    enriched = 0
    for event_id in event_ids:
        already = session.exec(
            select(EnrichedItem).where(EnrichedItem.event_id == event_id)
        ).first()
        if already is not None:
            continue
        event = session.get(Event, event_id)
        if event is None:
            continue
        if enricher.enrich_event(session, event) is not None:
            enriched += 1
    return enriched
