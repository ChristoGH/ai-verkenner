"""Load the `prompts/` templates and render per-item inputs (M4).

The markdown template is used as the **system** prompt (it carries the role, rules, and output
schema); the per-item facts plus a "JSON only" instruction become the **user** message. Templates
are read from the configurable `PROMPTS_DIR`.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache

from app.core.config import settings

CLASSIFY = "classify_item.md"
SUMMARISE = "summarise_item.md"
WEAK_SIGNAL = "weak_signal.md"
EXTRACT_GRAPH = "extract_graph.md"


@lru_cache(maxsize=None)
def load_template(name: str) -> str:
    """Read a prompt template by filename from PROMPTS_DIR (cached)."""
    return (settings.prompts_dir / name).read_text(encoding="utf-8")


def render_item_inputs(
    *,
    title: str,
    source_name: str,
    source_url: str,
    published_at: datetime | None,
    content: str | None,
    user_context: str | None = None,
    instruction: str = "Respond with JSON only — no prose, no code fences.",
) -> str:
    """Build the user-message block of item facts the templates expect."""
    lines = [
        f"title: {title}",
        f"source_name: {source_name}",
        f"source_url: {source_url}",
        f"published_at: {published_at.isoformat() if published_at else 'unknown'}",
        f"content: {content or ''}",
    ]
    if user_context is not None:
        lines.append(f"user_context: {user_context}")
    lines.append("")
    lines.append(instruction)
    return "\n".join(lines)
