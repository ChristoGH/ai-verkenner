"""GraphRAG digest generator (M7) — composes ONE briefing over already-enriched Events.

The flow follows PHASE_1_PLAN §5 M7: **embed the period's themes → Qdrant retrieve → Neo4j expand →
LLM compose** the ten decision-oriented sections, with the weak-signals / research-radar sections
drawn from the hub-dampened convergence quadrant. Crucially, enrichment is **never re-run**: the
digest composes over the existing `EnrichedItem`s with a single composition LLM call (cheap), or the
deterministic fallback render when no provider is configured.

Degrade-don't-crash: with Qdrant down the retrieve step returns `None` and selection falls back to
the whole corpus (SQLite-only); with Neo4j down the graph signals are empty and the weak-signals
section ranks the quadrant by hype-aware salience. The digest still generates either way.

Reuses `api.dashboard_service` (load + signals) and `scoring.ranking` — it does not re-derive
ranking or the priority rule.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.api import dashboard_service
from app.core.config import settings
from app.digests import render, retrieve
from app.digests.sections import HORIZON_CLASSES, build_items, build_sections
from app.embeddings import Embedder
from app.enrichment.prompts import load_template
from app.enrichment.provider import LLMProvider
from app.graph import GraphStore
from app.graph.util import to_utc
from app.models import Digest, EnrichedItem, RawItem

logger = logging.getLogger(__name__)

_DIGEST_PROMPT = "digest.md"


def _event_published(session: Session, event_ids: list[int]) -> dict[int, datetime | None]:
    """Most recent known published time per Event (None when no member item carries one)."""
    out: dict[int, datetime | None] = {eid: None for eid in event_ids}
    if not event_ids:
        return out
    rows = session.exec(
        select(RawItem.event_id, RawItem.published_at).where(RawItem.event_id.in_(event_ids))
    ).all()
    for eid, published in rows:
        if eid is None:
            continue
        p = to_utc(published) if published else None
        if p is not None and (out.get(eid) is None or p > out[eid]):
            out[eid] = p
    return out


def _select_period(
    session: Session, rows: list[EnrichedItem], *, period_days: int, now: datetime
) -> tuple[list[EnrichedItem], datetime | None, datetime | None]:
    """The Events in the window (by published date), plus the period bounds.

    Items with an unknown published date are kept (never dropped). If the window would be empty, the
    whole corpus is used — a digest is never empty just because dates are sparse.
    """
    published = _event_published(session, [r.event_id for r in rows])
    if period_days and period_days > 0:
        since = now - timedelta(days=period_days)
        in_window = [r for r in rows if published[r.event_id] is None or published[r.event_id] >= since]
        selected = in_window or rows
    else:
        selected = rows
    known = [published[r.event_id] for r in selected if published[r.event_id] is not None]
    return selected, (min(known) if known else None), (max(known) if known else None)


def generate_digest(
    session: Session,
    *,
    provider: LLMProvider | None = None,
    embedder: Embedder | None = None,
    qdrant_client=None,
    graph_store: GraphStore | None = None,
    user_context: str | None = None,
    period_days: int | None = None,
    section_limit: int | None = None,
    high_hype: int | None = None,
    retrieve_limit: int | None = None,
    now: datetime | None = None,
) -> Digest:
    """Generate, persist, and return one decision-oriented digest over the current corpus."""
    now = now or datetime.now(timezone.utc)
    user_context = settings.user_context if user_context is None else user_context
    period_days = settings.digest_period_days if period_days is None else period_days
    section_limit = settings.digest_section_limit if section_limit is None else section_limit
    high_hype = settings.digest_high_hype if high_hype is None else high_hype
    retrieve_limit = settings.digest_retrieve_limit if retrieve_limit is None else retrieve_limit

    all_rows = dashboard_service.load_enriched(session)
    period_rows, period_start, period_end = _select_period(
        session, all_rows, period_days=period_days, now=now
    )

    # GraphRAG retrieve (Qdrant) — focus on the user's themes; None ⇒ SQLite-only.
    relevance = retrieve.theme_relevance(
        session, embedder=embedder, qdrant_client=qdrant_client,
        user_context=user_context, rows=period_rows, limit=retrieve_limit,
    )
    # Neo4j expand — convergence per Event (empty when Neo4j is down).
    signals = dashboard_service.compute_signals(session, graph_store, period_rows)
    graphrag = relevance is not None or bool(signals)

    # Theme relevance is a stable tiebreak: most-relevant first, so a capped section keeps the
    # items closest to the user's themes (rank_with_graph is a stable sort over this order).
    ordered = sorted(period_rows, key=lambda r: -(relevance or {}).get(r.event_id, 0.0))

    items = build_items(session, ordered, signals)
    data = build_sections(
        items, signals,
        high_hype=high_hype, section_limit=section_limit, graphrag=graphrag,
        period_start=period_start, period_end=period_end,
    )

    content, method = _compose(provider, data, user_context)

    digest = Digest(
        period_start=period_start,
        period_end=period_end,
        generated_at=now,
        content_md=content,
        method=method,
        item_count=data.item_count,
        noise_count=data.noise_count,
        graphrag=graphrag,
        event_ids=list(data.referenced_event_ids),
    )
    session.add(digest)
    session.commit()
    session.refresh(digest)
    logger.info(
        "generated digest %s via %s: events=%d body=%d noise=%d weak=%d graphrag=%s",
        digest.id, method, data.total_events, data.item_count, data.noise_count,
        len(data.weak_signals), graphrag,
    )
    return digest


def _compose(provider: LLMProvider | None, data, user_context: str) -> tuple[str, str]:
    """Compose the markdown — one LLM call when a provider is present, else the fallback render."""
    if provider is not None:
        try:
            raw = provider.complete(
                system=load_template(_DIGEST_PROMPT),
                user=render.render_llm_inputs(data, user_context=user_context),
            )
            if raw and raw.strip():
                return raw.strip() + "\n", "llm"
            logger.warning("digest LLM returned empty content; using fallback render")
        except Exception as exc:  # noqa: BLE001 — fail-safe; the digest still generates
            logger.warning("digest LLM composition failed; using fallback render: %s", exc)
    return render.render_markdown(data, user_context=user_context), "fallback"


# Re-export for callers/tests that want the quadrant constant alongside the generator.
__all__ = ["generate_digest", "HORIZON_CLASSES"]
