"""M7.5 writers — outputs dir + create-only vault notes, exercised entirely in a temp dir.

Never touches the real vault: the vault sink must only ever CREATE new notes and must never modify or
delete an existing file. These tests prove both, plus the frontmatter + backlink contract.
"""

from __future__ import annotations

import pytest

from app.posts import generate_posts
from app.posts.writer import VAULT_INBOX, write_outputs, write_vault_notes
from tests.posts_fixtures import converging_digest


def _bundle():
    return generate_posts(converging_digest(), digest_id=3)


def test_write_outputs_writes_all_drafts(tmp_path):
    bundle = _bundle()
    paths = write_outputs(bundle, tmp_path / "outputs" / "posts")
    assert len(paths) == len(bundle.drafts) == 6
    for p in paths:
        assert p.exists() and p.read_text().strip()


def test_vault_notes_are_created_with_frontmatter_and_backlink(tmp_path):
    paths = write_vault_notes(_bundle(), tmp_path)
    assert len(paths) == 6
    inbox = tmp_path / VAULT_INBOX
    assert inbox.is_dir()
    for p in paths:
        assert p.parent == inbox
        body = p.read_text()
        assert body.startswith("---\n")
        assert "type: post-draft" in body
        assert "tags: [post-draft, ai-verkenner]" in body
        assert "[[AI Verkenner]]" in body


def test_vault_writer_never_modifies_or_deletes_existing_files(tmp_path):
    inbox = tmp_path / VAULT_INBOX
    inbox.mkdir()
    pre_existing = inbox / "important-user-note.md"
    pre_existing.write_text("DO NOT TOUCH")

    # Two runs: the second must not clobber the first's notes, and neither touches the user's note.
    first = write_vault_notes(_bundle(), tmp_path)
    second = write_vault_notes(_bundle(), tmp_path)

    assert pre_existing.read_text() == "DO NOT TOUCH"      # untouched
    assert set(first).isdisjoint(second)                  # create-only: distinct files
    assert len(second) == 6 and all(p.exists() for p in first)  # nothing deleted


def test_vault_writer_requires_existing_vault(tmp_path):
    with pytest.raises(FileNotFoundError):
        write_vault_notes(_bundle(), tmp_path / "no-such-vault")
