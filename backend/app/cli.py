"""Command-line entry points for the store + enrichment path.

    python -m app.cli run                # ingest → SQLite + Qdrant → dedup → enrich new Events
    python -m app.cli run --no-enrich    # skip the enrichment step (M3 behaviour)
    python -m app.cli reindex            # rebuild the Qdrant 'items' collection purely from SQLite

Uses the configured DATABASE_URL, QDRANT_URL, embedder (EMBEDDER / EMBEDDING_MODEL), and LLM
provider (LLM_PROVIDER / LLM_MODEL). With no API key the run still enriches via the rule-based
fallback.
"""

from __future__ import annotations

import argparse
import logging

from app.db import qdrant
from app.db.sqlite import get_session, init_db
from app.embeddings import get_embedder
from app.enrichment import Enricher, get_provider
from app.sources.registry import load_sources_from_settings
from app.storage.dedup import reindex
from app.storage.pipeline import ingest_and_store

logger = logging.getLogger(__name__)


def _cmd_run(args: argparse.Namespace) -> int:
    init_db()
    result = load_sources_from_settings()
    enabled = [s for s in result.sources if s.enabled]
    embedder = get_embedder()
    client = qdrant.get_client()
    enricher = None if args.no_enrich else Enricher(get_provider())
    with get_session() as session:
        run = ingest_and_store(
            enabled,
            session=session,
            embedder=embedder,
            qdrant_client=client,
            enricher=enricher,
        )
    print(
        f"run: fetched={run.fetched_item_count} new={run.new_item_count} "
        f"embedded={run.embedded_count} enriched_events={run.enriched_event_count} "
        f"sources={run.sources_upserted}"
    )
    if run.ingestion.failed:
        print(f"  per-source failures: {[r.source_name for r in run.ingestion.failed]}")
    return 0


def _cmd_reindex(_args: argparse.Namespace) -> int:
    init_db()
    embedder = get_embedder()
    client = qdrant.get_client()
    with get_session() as session:
        count = reindex(session, qdrant_client=client, embedder=embedder)
    print(f"reindex: rebuilt qdrant 'items' from {count} SQLite item(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="app.cli", description="AI Verkenner store + enrich path")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="ingest + persist + embed + dedup + enrich")
    run_parser.add_argument(
        "--no-enrich", action="store_true", help="skip the M4 enrichment step"
    )
    run_parser.set_defaults(func=_cmd_run)
    sub.add_parser("reindex", help="rebuild Qdrant from SQLite").set_defaults(func=_cmd_reindex)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
