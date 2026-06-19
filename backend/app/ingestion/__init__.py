"""Ingestion: fetch the curated registry into in-memory RawItems, fail-safe per source."""

from app.ingestion.orchestrator import (
    IngestionRun,
    SourceRunResult,
    run_ingestion,
)

__all__ = ["run_ingestion", "IngestionRun", "SourceRunResult"]
