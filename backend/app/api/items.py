"""`/items` router — the ranked Core Radar feed (M6).

Ranked with `scoring.ranking.rank_with_graph`: priority class first (canonical), then hype-aware
salience blended with the graph signal. Filterable by `priority_class` and by mentioned `entity`
(used by the Cosmograph "click an entity → filter the list" interaction).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.dashboard_service import ranked_items
from app.api.deps import graph_store_dep, session_dep
from app.graph import GraphStore
from app.schemas.api import ItemOut

router = APIRouter(tags=["items"])


@router.get("/items", response_model=list[ItemOut])
def list_items(
    priority_class: str | None = Query(default=None, description="Filter by priority class."),
    entity: str | None = Query(default=None, description="Only items mentioning this entity."),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(session_dep),
    store: GraphStore | None = Depends(graph_store_dep),
) -> list[ItemOut]:
    """Return ranked enriched items (Core Radar)."""
    return ranked_items(
        session, store, priority_class=priority_class, entity=entity, limit=limit
    )
