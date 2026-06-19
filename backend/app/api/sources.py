"""`/sources` router — read the curated registry.

The registry is human-curated and file-based (no create/edit via the API by design — see Task
002). This endpoint loads, validates, and returns the configured sources, filterable by
`enabled`. Malformed entries are skipped and reported (logged); they never 500 the request.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.source import Source
from app.sources.registry import load_sources_from_settings

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[Source])
def list_sources(
    enabled: bool | None = Query(
        default=None,
        description="Filter by enabled flag; omit to return all configured sources.",
    ),
) -> list[Source]:
    """Return the validated, configured sources (optionally filtered by `enabled`)."""
    result = load_sources_from_settings()
    sources = result.sources
    if enabled is not None:
        sources = [s for s in sources if s.enabled == enabled]
    return sources
