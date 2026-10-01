"""Write the M7.5 drafts to disk — a git-ignored working dir, and (optionally) the Obsidian vault.

Two sinks:

- `write_outputs` — writes each draft as markdown under `outputs/posts/` (git-ignored). This is a
  scratch/working area; a same-day re-run overwrites its own files.
- `write_vault_notes` — **create-only**. When a vault dir is configured, each draft is written as a
  *new* note in `<vault>/00-Inbox/` with post-draft frontmatter and an `[[AI Verkenner]]` backlink.
  It never modifies or deletes an existing file: the target name is made unique with a numeric suffix
  before writing, so an existing note is never opened for writing. This is the hard guardrail on
  touching the user's real vault.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.posts.model import VAULT_BACKLINK, Draft, PostBundle

logger = logging.getLogger(__name__)

VAULT_INBOX = "00-Inbox"


def _date(bundle: PostBundle) -> str:
    return bundle.generated_at.date().isoformat()


def write_outputs(bundle: PostBundle, out_dir: Path) -> list[Path]:
    """Write each draft to `<out_dir>/<date>-<slug>.md`; return the paths (newest run wins)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for draft in bundle.drafts:
        path = out_dir / f"{_date(bundle)}-{draft.slug}.md"
        path.write_text(draft.text)
        written.append(path)
    logger.info("wrote %d draft(s) to %s", len(written), out_dir)
    return written


def _frontmatter(bundle: PostBundle, draft: Draft) -> str:
    return (
        "---\n"
        "type: post-draft\n"
        "tags: [post-draft, ai-verkenner]\n"
        f"created: {bundle.generated_at.isoformat()}\n"
        f"surface: {draft.surface}\n"
        f"piece: {draft.piece}\n"
        f"digest_id: {bundle.digest_id if bundle.digest_id is not None else 'null'}\n"
        "---\n\n"
        f"{VAULT_BACKLINK}\n\n"
    )


def _unique_new_path(directory: Path, stem: str, suffix: str = ".md") -> Path:
    """A path that does NOT already exist — never returns an existing file (create-only)."""
    candidate = directory / f"{stem}{suffix}"
    n = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{n}{suffix}"
        n += 1
    return candidate


def write_vault_notes(bundle: PostBundle, vault_dir: Path) -> list[Path]:
    """Create new post-draft notes in `<vault>/00-Inbox/`. Never modifies or deletes existing files.

    Raises FileNotFoundError if the vault directory does not exist — we create notes *inside* an
    existing vault, never fabricate a vault at an arbitrary path.
    """
    if not vault_dir.exists():
        raise FileNotFoundError(f"vault dir does not exist: {vault_dir}")
    inbox = vault_dir / VAULT_INBOX
    inbox.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for draft in bundle.drafts:
        stem = f"{_date(bundle)}-ai-verkenner-{draft.slug}"
        path = _unique_new_path(inbox, stem)  # guaranteed non-existent ⇒ create-only
        path.write_text(_frontmatter(bundle, draft) + draft.text)
        written.append(path)
    logger.info("created %d vault note(s) in %s (create-only)", len(written), inbox)
    return written


__all__ = ["write_outputs", "write_vault_notes", "VAULT_INBOX"]
