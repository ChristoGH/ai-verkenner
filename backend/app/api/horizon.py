"""`/horizon` router — THE weak-signal view (M6).

This is **not** the Core Radar ordering. It selects the `horizon_signal`/`archive` quadrant — the
low-relevance items a class-first feed buries — and ranks THEM by **graph convergence** (distinct
sources touching the same entity). It is the query that makes the "Weak Signal of the Week"
reachable: quietly-emerging developments rise to the top, each with its `why` and contributing
sources. Degrades cleanly (graph-less ordering) when Neo4j is down.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.dashboard_service import horizon_items
from app.api.deps import graph_store_dep, session_dep
from app.graph import GraphStore
from app.schemas.api import HorizonOut

router = APIRouter(tags=["horizon"])


@router.get("/horizon", response_model=HorizonOut)
def get_horizon(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(session_dep),
    store: GraphStore | None = Depends(graph_store_dep),
) -> HorizonOut:
    """Return the weak-signal quadrant ranked by graph convergence."""
    items = horizon_items(session, store, limit=limit)
    return HorizonOut(items=items, graph_available=store is not None)
