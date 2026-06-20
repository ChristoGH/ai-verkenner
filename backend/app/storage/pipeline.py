"""The run path: ingest → persist (SQLite) → embed + dedup (Qdrant) → enrich (M4) → graph (M5).

Order matters and encodes the ADR-0001 invariant: **SQLite first**. Sources and RawItems are
committed to the system of record before any derived-store call, so a Qdrant/Neo4j failure can only
cost a rebuildable index, never a record. Enrichment runs **after dedup** (once per real-world
development); the Neo4j projection runs **after enrichment** and is degrade-don't-crash.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from qdrant_client import QdrantClient
from sqlmodel import Session

from app.core.config import settings
from app.embeddings import Embedder
from app.enrichment import Enricher, enrich_new_events
from app.graph import GraphStore, project_new_events
from app.ingestion import run_ingestion
from app.ingestion.orchestrator import IngestionRun
from app.schemas.source import Source
from app.storage.dedup import assign_events
from app.storage.repository import persist_new_items, upsert_sources

logger = logging.getLogger(__name__)


@dataclass
class StoreRunResult:
    """Outcome of one store run."""

    ingestion: IngestionRun
    sources_upserted: int
    new_item_count: int
    embedded_count: int
    enriched_event_count: int = 0
    projected_event_count: int = 0

    @property
    def fetched_item_count(self) -> int:
        return len(self.ingestion.items)


def ingest_and_store(
    sources: list[Source],
    *,
    session: Session,
    embedder: Embedder,
    qdrant_client: QdrantClient | None,
    tau: float | None = None,
    enricher: Enricher | None = None,
    graph_store: GraphStore | None = None,
) -> StoreRunResult:
    """Run the full path for the given sources. Fail-safe per source (M1) is preserved.

    `qdrant_client=None` (or unreachable Qdrant) degrades dedup to hash-only; `enricher=None` skips
    enrichment (M3 behaviour); `graph_store=None` skips the Neo4j projection (M4 behaviour). Each
    derived store degrades independently — items persist to SQLite regardless.
    """
    tau = settings.dedup_tau if tau is None else tau

    run = run_ingestion(sources)

    # SQLite FIRST — the system of record.
    source_ids = upsert_sources(session, sources)
    new_rows = persist_new_items(session, run.items, source_ids)

    # Then the derived index + Event grouping (degrades if Qdrant is down).
    assign_events(session, new_rows, qdrant_client=qdrant_client, embedder=embedder, tau=tau)

    # Then enrich the new Events (idempotent; only events without an EnrichedItem).
    enriched_event_count = 0
    if enricher is not None:
        enriched_event_count = enrich_new_events(session, enricher, new_rows)

    # Then project the new, enriched Events into Neo4j (idempotent; degrade-don't-crash).
    projected_event_count = 0
    if graph_store is not None:
        projected_event_count = project_new_events(session, graph_store, new_rows)

    embedded_count = sum(1 for r in new_rows if r.embedded)
    logger.info(
        "store run: fetched=%d new=%d embedded=%d enriched_events=%d projected_events=%d "
        "(tau=%.2f)",
        len(run.items), len(new_rows), embedded_count, enriched_event_count,
        projected_event_count, tau,
    )
    return StoreRunResult(
        ingestion=run,
        sources_upserted=len(source_ids),
        new_item_count=len(new_rows),
        embedded_count=embedded_count,
        enriched_event_count=enriched_event_count,
        projected_event_count=projected_event_count,
    )
