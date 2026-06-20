"""`/graph` router — the Cosmograph projection (M6).

Projects Neo4j into `{nodes, links}` for `@cosmograph/react`. Kept legible by default: top entities
(by interaction degree) + the events that mention them, capped to `limit`, optionally filtered by a
recency `window_days` and a `priority` class. Degrades to an empty, `available: false` graph when
Neo4j is unreachable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import graph_store_dep
from app.graph import GraphStore
from app.schemas.api import GraphLinkOut, GraphNodeOut, GraphOut

router = APIRouter(tags=["graph"])


@router.get("/graph", response_model=GraphOut)
def get_graph(
    limit: int = Query(default=150, ge=1, le=1000, description="Max nodes (kept readable)."),
    window_days: int | None = Query(default=None, description="Only edges newer than N days."),
    priority: str | None = Query(default=None, description="Only events of this priority class."),
    store: GraphStore | None = Depends(graph_store_dep),
) -> GraphOut:
    """Return capped nodes/links for the network + timeline view."""
    if store is None:
        return GraphOut(nodes=[], links=[], truncated=False, available=False)
    view = store.graph_view(limit=limit, window_days=window_days, priority=priority)
    return GraphOut(
        nodes=[GraphNodeOut(**n.__dict__) for n in view.nodes],
        links=[GraphLinkOut(**l.__dict__) for l in view.links],
        truncated=view.truncated,
        available=True,
    )
