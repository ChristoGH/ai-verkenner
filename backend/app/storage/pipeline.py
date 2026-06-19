"""The M3 run path: ingest → persist (SQLite) → embed + dedup (Qdrant) → Events.

Order matters and encodes the ADR-0001 invariant: **SQLite first**. Sources and RawItems are
committed to the system of record before any Qdrant call, so a vector-store failure can only cost
us the derived index (rebuildable via `reindex`), never a record.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from qdrant_client import QdrantClient
from sqlmodel import Session

from app.core.config import settings
from app.embeddings import Embedder
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
) -> StoreRunResult:
    """Run the full M3 path for the given sources. Fail-safe per source (M1) is preserved.

    `qdrant_client=None` (or an unreachable Qdrant) degrades dedup to hash-only; items persist to
    SQLite regardless.
    """
    tau = settings.dedup_tau if tau is None else tau

    run = run_ingestion(sources)

    # SQLite FIRST — the system of record.
    source_ids = upsert_sources(session, sources)
    new_rows = persist_new_items(session, run.items, source_ids)

    # Then the derived index + Event grouping (degrades if Qdrant is down).
    assign_events(session, new_rows, qdrant_client=qdrant_client, embedder=embedder, tau=tau)

    embedded_count = sum(1 for r in new_rows if r.embedded)
    logger.info(
        "store run: fetched=%d new=%d embedded=%d (tau=%.2f)",
        len(run.items), len(new_rows), embedded_count, tau,
    )
    return StoreRunResult(
        ingestion=run,
        sources_upserted=len(source_ids),
        new_item_count=len(new_rows),
        embedded_count=embedded_count,
    )
