"""Health & readiness router.

`GET /health` is **liveness**: it always returns 200 with the service identity as long as the
process is up, and additionally reports per-store reachability under `dependencies`. A store being
down (Qdrant/Neo4j) is surfaced there but never turns /health into a 5xx — the app degrades, it
does not crash (CLAUDE.md: SQLite is the source of truth; the derived stores are rebuildable).

`GET /health/ready` is **readiness**: it returns 503 when a required store is unreachable, for
callers (e.g. an orchestrator) that need every dependency before sending traffic.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.db import DependencyStatus, neo4j, qdrant

router = APIRouter(tags=["health"])


def _dependency_statuses() -> list[DependencyStatus]:
    """Ping every required store. Each ping degrades rather than raises."""
    return [qdrant.ping(), neo4j.ping()]


@router.get("/health")
def health() -> dict[str, object]:
    """Liveness probe — always 200 while the process runs; reports store reachability.

    Backward-compatible: `status`, `service`, and `version` are unchanged; `dependencies` is
    additive.
    """
    deps = _dependency_statuses()
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.app_version,
        "dependencies": {d.name: d.status for d in deps},
    }


@router.get("/health/ready")
def ready(response: Response) -> dict[str, object]:
    """Readiness probe — 200 only when every required store is reachable, else 503."""
    deps = _dependency_statuses()
    all_ready = all(d.ok for d in deps)
    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if all_ready else "not_ready",
        "service": settings.service_name,
        "version": settings.app_version,
        "dependencies": {
            d.name: {"status": d.status, "detail": d.detail} for d in deps
        },
    }
