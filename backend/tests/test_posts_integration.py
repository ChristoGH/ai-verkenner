"""M7.5 end-to-end over a REAL seeded SQLite corpus (still offline: in-memory DB + InMemoryGraph).

Proves the non-CLI path the `posts` command drives: build the structured digest data from the DB
(LLM-free), project it into drafts, and write create-only vault notes — over the same seed the M7
digest tests use (which contains a genuine two-source convergence and two noise demotions).
"""

from __future__ import annotations

from app.digests import build_digest_data
from app.posts import (
    PIECE_NOISE_REPORT,
    PIECE_WEAK_SIGNAL,
    SURFACE_MEDIUM,
    generate_posts,
    weak_cluster,
)
from app.posts.writer import write_vault_notes
from tests.test_digest import _store_with_seed


def test_posts_over_seeded_corpus(session, tmp_path):
    store, seeded = _store_with_seed(session)
    data = build_digest_data(session, graph_store=store, period_days=0)

    cluster, converged = weak_cluster(data)
    bundle = generate_posts(data, digest_id=1)

    assert len(bundle.drafts) == 6
    # The seed's two RAG developments converge across two distinct sources → a real weak signal.
    assert converged is True and bundle.has_convergence is True

    # The Noise Report carries the seeded archive + hype-5 demotions, with their links preserved.
    noise_medium = next(d for d in bundle.drafts
                        if d.piece == PIECE_NOISE_REPORT and d.surface == SURFACE_MEDIUM)
    assert "https://src3/arc" in noise_medium.text
    assert "https://src3/hype" in noise_medium.text

    # The weak-signal drafts keep the two converging RAG source links.
    weak_medium = next(d for d in bundle.drafts
                       if d.piece == PIECE_WEAK_SIGNAL and d.surface == SURFACE_MEDIUM)
    assert "/rag0" in weak_medium.text and "/rag1" in weak_medium.text

    # Vault notes are created (temp dir), one per draft.
    notes = write_vault_notes(bundle, tmp_path)
    assert len(notes) == len(bundle.drafts) == 6


def test_cli_module_imports_cleanly():
    import app.cli  # noqa: F401 — importing exercises the full posts wiring (no broken imports)
