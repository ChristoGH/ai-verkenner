"""Command-line entry points for the store + enrichment + graph path.

    python -m app.cli run                # ingest → SQLite + Qdrant → dedup → enrich → project (Neo4j)
    python -m app.cli run --no-enrich    # skip the enrichment step (M3 behaviour)
    python -m app.cli run --no-graph     # skip the Neo4j projection (M4 behaviour)
    python -m app.cli reindex            # rebuild the Qdrant 'items' collection purely from SQLite
    python -m app.cli graph-reindex      # rebuild the Neo4j graph purely from SQLite
    python -m app.cli digest             # compose a GraphRAG weekly digest over enriched Events (M7)
    python -m app.cli digest --days 14   # widen the digest window (0 = the whole corpus)
    python -m app.cli posts              # project the latest digest into X/LinkedIn/Medium DRAFTS (M7.5)
    python -m app.cli posts --digest 3 --vault-dir ~/vault   # a specific digest + write vault notes

Uses the configured DATABASE_URL, QDRANT_URL, NEO4J_*, embedder, and LLM provider. With no API key
the run still enriches via the rule-based fallback; with Neo4j down the projection degrades and the
run still completes. `posts` is LLM-free and never posts — it writes draft files only.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db import qdrant
from app.db.neo4j import get_driver
from app.db.sqlite import get_session, init_db
from app.digests import build_digest_data, generate_digest
from app.embeddings import get_embedder
from app.enrichment import Enricher, get_provider
from app.graph import Neo4jGraphStore, graph_reindex
from app.models import Digest
from app.posts import generate_posts, weak_cluster
from app.posts.image import export_convergence_image
from app.posts.writer import write_outputs, write_vault_notes
from app.sources.registry import load_sources_from_settings
from app.storage.dedup import reindex
from app.storage.pipeline import ingest_and_store
from sqlmodel import select

logger = logging.getLogger(__name__)


def _cmd_run(args: argparse.Namespace) -> int:
    init_db()
    result = load_sources_from_settings()
    enabled = [s for s in result.sources if s.enabled]
    embedder = get_embedder()
    client = qdrant.get_client()
    enricher = None if args.no_enrich else Enricher(get_provider())
    graph_store = None if args.no_graph else Neo4jGraphStore(get_driver())
    with get_session() as session:
        run = ingest_and_store(
            enabled,
            session=session,
            embedder=embedder,
            qdrant_client=client,
            enricher=enricher,
            graph_store=graph_store,
        )
    print(
        f"run: fetched={run.fetched_item_count} new={run.new_item_count} "
        f"embedded={run.embedded_count} enriched_events={run.enriched_event_count} "
        f"projected_events={run.projected_event_count} sources={run.sources_upserted}"
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


def _cmd_graph_reindex(_args: argparse.Namespace) -> int:
    init_db()
    store = Neo4jGraphStore(get_driver())
    with get_session() as session:
        count = graph_reindex(session, store)
    print(f"graph-reindex: rebuilt Neo4j from {count} enriched Event(s)")
    return 0


def _cmd_digest(args: argparse.Namespace) -> int:
    from app.db import neo4j

    init_db()
    embedder = get_embedder()
    client = qdrant.get_client()
    provider = get_provider()
    # Degrade-don't-crash: skip the Neo4j expand when the graph is unreachable.
    graph_store = Neo4jGraphStore(get_driver()) if neo4j.ping().ok else None
    period_days = None if args.days is None else args.days
    with get_session() as session:
        digest = generate_digest(
            session,
            provider=provider,
            embedder=embedder,
            qdrant_client=client,
            graph_store=graph_store,
            period_days=period_days,
        )
    print(
        f"digest: id={digest.id} method={digest.method} graphrag={digest.graphrag} "
        f"body={digest.item_count} noise={digest.noise_count} "
        f"events={len(digest.event_ids)} period={digest.period_start}..{digest.period_end}"
    )
    return 0


def _load_digest(session, which: str) -> Digest | None:
    """Resolve `--digest`: 'latest' (newest by generated_at) or a numeric id. None if not found."""
    if which == "latest":
        return session.exec(select(Digest).order_by(Digest.generated_at.desc())).first()
    try:
        digest_id = int(which)
    except ValueError:
        return None
    return session.get(Digest, digest_id)


def _cmd_posts(args: argparse.Namespace) -> int:
    from app.db import neo4j

    init_db()
    embedder = get_embedder()
    client = qdrant.get_client()
    # Degrade-don't-crash: skip the Neo4j expand when the graph is unreachable (weak signals then
    # fall back to salience — no convergence claimed).
    graph_store = Neo4jGraphStore(get_driver()) if neo4j.ping().ok else None
    period_days = None if args.days is None else args.days
    now = datetime.now(timezone.utc)

    with get_session() as session:
        digest = _load_digest(session, args.digest)
        if digest is None:
            print(f"posts: no digest for --digest {args.digest!r}; "
                  f"run `python -m app.cli digest` first")
            return 1
        # Re-derive the structured digest (deterministic, LLM-free) and project it into drafts.
        data = build_digest_data(
            session, embedder=embedder, qdrant_client=client,
            graph_store=graph_store, period_days=period_days, now=now,
        )
        cluster, converged = weak_cluster(data)
        out_dir = settings.posts_output_dir
        image = export_convergence_image(
            cluster, out_dir / f"{now.date().isoformat()}-weak-signal-cluster.png"
        )
        bundle = generate_posts(data, digest_id=digest.id, generated_at=now, image_ref=image.ref)
        out_paths = write_outputs(bundle, out_dir)

        vault_dir = Path(args.vault_dir) if args.vault_dir else settings.vault_dir
        vault_paths = write_vault_notes(bundle, vault_dir) if vault_dir else []

    img_kind = "placeholder (screenshot Cosmograph)" if image.is_placeholder else str(image.path)
    print(
        f"posts: digest={digest.id} convergence={converged} drafts={len(bundle.drafts)} "
        f"image={img_kind} out_dir={out_dir}"
    )
    print(f"  wrote {len(out_paths)} draft file(s); "
          + (f"created {len(vault_paths)} vault note(s) in {vault_dir}/00-Inbox"
             if vault_paths else "no vault dir configured (set --vault-dir or VAULT_DIR)"))
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="app.cli", description="AI Verkenner store/enrich/graph")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="ingest + persist + embed + dedup + enrich + project")
    run_parser.add_argument("--no-enrich", action="store_true", help="skip the M4 enrichment step")
    run_parser.add_argument("--no-graph", action="store_true", help="skip the M5 Neo4j projection")
    run_parser.set_defaults(func=_cmd_run)
    sub.add_parser("reindex", help="rebuild Qdrant from SQLite").set_defaults(func=_cmd_reindex)
    sub.add_parser(
        "graph-reindex", help="rebuild Neo4j from SQLite"
    ).set_defaults(func=_cmd_graph_reindex)
    digest_parser = sub.add_parser("digest", help="compose a GraphRAG weekly digest (M7)")
    digest_parser.add_argument(
        "--days", type=int, default=None,
        help="digest window in days (0 = whole corpus; default from DIGEST_PERIOD_DAYS)",
    )
    digest_parser.set_defaults(func=_cmd_digest)
    posts_parser = sub.add_parser(
        "posts", help="project a digest into X/LinkedIn/Medium DRAFTS (M7.5; never posts)"
    )
    posts_parser.add_argument(
        "--digest", default="latest", help="digest id or 'latest' (default: latest)"
    )
    posts_parser.add_argument(
        "--vault-dir", default=None,
        help="Obsidian vault dir; also create notes in <vault>/00-Inbox/ (default from VAULT_DIR)",
    )
    posts_parser.add_argument(
        "--days", type=int, default=None,
        help="re-derive window in days (0 = whole corpus; default from DIGEST_PERIOD_DAYS)",
    )
    posts_parser.set_defaults(func=_cmd_posts)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
