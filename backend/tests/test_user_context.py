"""Task 017 — `docs/USER_CONTEXT.md` reaches the runtime, and no fall-back is silent.

The defect being pinned (D-069, raised by task 015's revert in D-062): `docs/USER_CONTEXT.md` opens
by calling itself *"the ground truth AI Verkenner uses to score `relevance`"* and was referenced in
**no Python file**. `USER_CONTEXT` was unset, so `config.py` fell through to a 309-character literal
stub naming no vendor and no open decision. Every `relevance` score the project ever measured —
D-018's corpus baseline included — was computed against that stub, and $4.77 of prompt-wording
calibration was spent before anything said so.

These tests are offline and deterministic: no LLM, no network, no corpus. They drive the real
`Settings` construction path rather than a helper in isolation, because the defect was precisely
that the shipped path did something other than the documents claimed.

`_load_user_context` reads `USER_CONTEXT` from the process environment, so every test that cares
about precedence must control it — `monkeypatch.delenv(..., raising=False)` — rather than assuming
the developer's shell is clean.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app.core import config as config_module
from app.core.config import (
    REPO_ROOT,
    Settings,
    _DEFAULT_USER_CONTEXT,
    log_user_context_source,
    settings,
)


@pytest.fixture()
def clean_env(monkeypatch):
    """No inherited USER_CONTEXT / USER_CONTEXT_PATH — precedence is what is under test."""
    monkeypatch.delenv("USER_CONTEXT", raising=False)
    monkeypatch.delenv("USER_CONTEXT_PATH", raising=False)
    return monkeypatch


def test_user_context_loads_from_file(clean_env, tmp_path: Path):
    """The configured file is read, and its content — not the stub — becomes `user_context`."""
    doc = tmp_path / "USER_CONTEXT.md"
    doc.write_text(
        "# Who\n\nARQ Platform on AKS with Knative. Open decision: Lakebase pgvector vs Qdrant.\n",
        encoding="utf-8",
    )
    clean_env.setenv("USER_CONTEXT_PATH", str(doc))

    s = Settings()

    assert "Lakebase pgvector vs Qdrant" in s.user_context
    assert s.user_context != _DEFAULT_USER_CONTEXT
    # The source is named, not merely correct — that naming is the whole point of the task.
    assert str(doc) in s.user_context_source


def test_user_context_reaches_the_enricher(clean_env, tmp_path: Path):
    """Not just parsed — actually interpolated into the classify call's user message.

    `prompts.render_item_inputs` is the exact renderer `Enricher` and `measure_calibration.py` both
    use, so this pins the delivery path the $4.77 of prior runs silently missed.
    """
    from app.enrichment import prompts

    doc = tmp_path / "ctx.md"
    doc.write_text("Christo builds Commission Intelligence with Qdrant + Neo4j + Claude SDK.\n",
                   encoding="utf-8")
    clean_env.setenv("USER_CONTEXT_PATH", str(doc))
    s = Settings()

    rendered = prompts.render_item_inputs(
        title="Anthropic ships an Agent SDK change",
        source_name="Example",
        source_url="https://example.com/a",
        published_at=None,
        content="body",
        user_context=s.user_context,
    )

    assert "Claude SDK" in rendered
    assert "user_context:" in rendered


def test_explicit_env_overrides_file(clean_env, tmp_path: Path):
    """An explicit USER_CONTEXT wins over the file, so one run can override for an experiment."""
    doc = tmp_path / "USER_CONTEXT.md"
    doc.write_text("FILE CONTEXT — should not win\n", encoding="utf-8")
    clean_env.setenv("USER_CONTEXT_PATH", str(doc))
    clean_env.setenv("USER_CONTEXT", "ENV CONTEXT — wins")

    s = Settings()

    assert s.user_context == "ENV CONTEXT — wins"
    assert "FILE CONTEXT" not in s.user_context
    assert "explicit override" in s.user_context_source

    # A blank/whitespace USER_CONTEXT is NOT an override — it must not silently blank the context,
    # which would be the original defect with an emptier stub.
    clean_env.setenv("USER_CONTEXT", "   ")
    assert Settings().user_context.strip() == "FILE CONTEXT — should not win"


def test_missing_file_falls_back_and_logs(clean_env, tmp_path: Path, caplog):
    """An absent configured file → the default, and the fall-back is LOUD, not silent.

    Asserts the LOG, not just the value. Addendum §7: a silent fallback is a defect, not a
    convenience — this is the exact failure mode task 017 exists to make impossible to repeat.
    WARNING (not INFO) because logging is frequently unconfigured when settings are constructed.
    """
    missing = tmp_path / "does-not-exist.md"
    clean_env.setenv("USER_CONTEXT_PATH", str(missing))

    with caplog.at_level(logging.WARNING, logger="app.core.config"):
        s = Settings()

    assert s.user_context == _DEFAULT_USER_CONTEXT
    assert "built-in default" in s.user_context_source

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings, "the fall-back to the stub was SILENT — that is the D-069 defect"
    message = warnings[0].getMessage()
    assert str(missing) in message
    assert "D-069" in message


def test_empty_file_also_falls_back_and_logs(clean_env, tmp_path: Path, caplog):
    """A present-but-empty file is a fall-back too — and equally loud."""
    empty = tmp_path / "USER_CONTEXT.md"
    empty.write_text("   \n\n", encoding="utf-8")
    clean_env.setenv("USER_CONTEXT_PATH", str(empty))

    with caplog.at_level(logging.WARNING, logger="app.core.config"):
        s = Settings()

    assert s.user_context == _DEFAULT_USER_CONTEXT
    assert [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_user_context_path_uses_existing_base_path_convention(clean_env):
    """No second path convention was introduced — this resolves exactly as task 014's setting does.

    Pins both halves of `_resolve`: a relative path hangs off REPO_ROOT, an absolute path is left
    alone. If someone later hardcodes a path or adds a parallel resolver, this fails.
    """
    clean_env.setenv("USER_CONTEXT_PATH", "docs/USER_CONTEXT.md")
    clean_env.setenv("ENTITY_ALIASES_FILE", "sources/entity_aliases.yaml")
    s = Settings()

    assert s.user_context_path == REPO_ROOT / "docs/USER_CONTEXT.md"
    assert s.user_context_path.is_absolute()
    # Same mechanism as the sibling root-level content settings, not a lookalike.
    assert s.user_context_path.parent.parent == s.entity_aliases_file.parent.parent == REPO_ROOT

    clean_env.setenv("USER_CONTEXT_PATH", "/tmp/elsewhere/ctx.md")
    assert Settings().user_context_path == Path("/tmp/elsewhere/ctx.md")


def test_default_path_is_the_real_document(clean_env):
    """With nothing set, the runtime uses docs/USER_CONTEXT.md — the file the docs always claimed."""
    s = Settings()
    assert s.user_context_path == REPO_ROOT / "docs/USER_CONTEXT.md"


def test_shipped_runtime_uses_the_real_document_not_the_stub():
    """The module-level `settings` singleton — what the enricher actually reads — is not the stub.

    Guards the regression in the direction that matters: this asserted `False` before task 017.
    """
    assert settings.user_context != _DEFAULT_USER_CONTEXT
    assert "Qdrant" in settings.user_context and "Claude" in settings.user_context
    assert str(settings.user_context_path) in settings.user_context_source


def test_log_user_context_source_announces_once(monkeypatch, caplog):
    """The startup announcement fires once per process and names the source."""
    monkeypatch.setattr(config_module, "_user_context_announced", False)

    with caplog.at_level(logging.INFO, logger="app.core.config"):
        first = log_user_context_source()
        second = log_user_context_source()

    assert first == second
    assert settings.user_context_source in first
    announcements = [r for r in caplog.records if "user_context source in force" in r.getMessage()]
    assert len(announcements) == 1, "the announcement must not repeat on every call"
