"""Command-line entry points for the M3 store path.

    python -m app.cli run       # ingest enabled sources → SQLite + Qdrant, dedup into Events
    python -m app.cli reindex   # rebuild the Qdrant 'items' collection purely from SQLite

Both use the configured DATABASE_URL, QDRANT_URL, and embedder (EMBEDDER / EMBEDDING_MODEL).
"""

from __future__ import annotations

import argparse
import logging

from app.db import qdrant
from app.db.sqlite import get_session, init_db
from app.embeddings import get_embedder
from app.sources.registry import load_sources_from_settings
from app.storage.dedup import reindex
from app.storage.pipeline import ingest_and_store

logger = logging.getLogger(__name__)


def _cmd_run(_args: argparse.Namespace) -> int:
    init_db()
    result = load_sources_from_settings()
    enabled = [s for s in result.sources if s.enabled]
    embedder = get_embedder()
    client = qdrant.get_client()
    with get_session() as session:
        run = ingest_and_store(
            enabled, session=session, embedder=embedder, qdrant_client=client
        )
    print(
        f"run: fetched={run.fetched_item_count} new={run.new_item_count} "
        f"embedded={run.embedded_count} sources={run.sources_upserted}"
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
    parser = argparse.ArgumentParser(prog="app.cli", description="AI Verkenner store path (M3)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="ingest + persist + embed + dedup").set_defaults(func=_cmd_run)
    sub.add_parser("reindex", help="rebuild Qdrant from SQLite").set_defaults(func=_cmd_reindex)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
