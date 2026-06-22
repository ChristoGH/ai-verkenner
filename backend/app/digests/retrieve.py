"""GraphRAG retrieve step for the digest (M7) — theme embed → Qdrant retrieve → Event pool.

The digest is *focused* on the user's themes: we embed a theme query (the user context, grounded in
the period's most common tags) and ask Qdrant for the nearest item vectors, then map those back to
Events. That focused pool is what the section router draws the body from — so a large corpus still
produces a tight, relevant briefing.

This step is **best-effort and degradable**: any failure (Qdrant down, no embedder, empty index)
returns `None`, and the generator falls back to SQLite-only selection (the whole corpus). It never
raises into the run — exactly the degrade-don't-crash discipline of the M3 Qdrant path.
"""

from __future__ import annotations

import logging
from collections import Counter

from sqlmodel import Session

from app.db import qdrant_index
from app.embeddings import Embedder
from app.models import EnrichedItem, RawItem

logger = logging.getLogger(__name__)


def build_theme_text(user_context: str, rows: list[EnrichedItem], *, top_tags: int = 12) -> str:
    """The theme query: the user context, grounded in the period's most frequent tags."""
    counter: Counter[str] = Counter()
    for r in rows:
        for tag in (r.tags or []):
            counter[str(tag).lower()] += 1
    tags = [tag for tag, _ in counter.most_common(top_tags)]
    if tags:
        return f"{user_context}\n\nThemes this period: {', '.join(tags)}"
    return user_context


def theme_relevance(
    session: Session,
    *,
    embedder: Embedder | None,
    qdrant_client,
    user_context: str,
    rows: list[EnrichedItem],
    limit: int,
) -> dict[int, float] | None:
    """Per-Event theme relevance (best cosine to the theme query) via Qdrant; `None` when degraded.

    Maps each nearest item vector back to its Event and keeps the best similarity per Event. Returns
    `None` (degrade to SQLite-only) when there is no embedder/client, the index is empty, or anything
    raises — never into the run.
    """
    if embedder is None or qdrant_client is None or not rows:
        return None
    try:
        text = build_theme_text(user_context, rows)
        vector = embedder.embed([text])[0]
        neighbours = qdrant_index.search_neighbours(qdrant_client, vector, limit=limit)
        scores: dict[int, float] = {}
        for hit in neighbours:
            item = session.get(RawItem, hit.item_id)
            if item is not None and item.event_id is not None:
                prev = scores.get(item.event_id)
                if prev is None or hit.score > prev:
                    scores[item.event_id] = hit.score
        return scores or None
    except Exception as exc:  # noqa: BLE001 — degrade-don't-crash; SQLite-only fallback
        logger.warning("digest GraphRAG retrieve unavailable; using SQLite-only selection: %s", exc)
        return None
