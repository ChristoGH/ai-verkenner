"""Deterministic hashes for dedup (M3).

Two distinct, documented hashes (see `app/models/entities.py` for why they differ):

- `dedup_key(...)`   — *identity*: stable over (source, url, title, published). Drives idempotency
                       (same item on a re-run → same key → not re-inserted). Different sources keep
                       distinct keys because their URLs differ.
- `content_hash(...)`— *content fingerprint*: over normalised title+summary. Stage-(a) of dedup;
                       byte-identical coverage from different sources collapses to one Event.

Both are SHA-256 hex (stable across processes/runs).
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

_WS_RE = re.compile(r"\s+")


def _normalize(text: str | None) -> str:
    """Lowercase, collapse whitespace, strip — so trivial formatting noise doesn't change a hash."""
    if not text:
        return ""
    return _WS_RE.sub(" ", text.strip().lower())


def _sha256(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\x1f")  # unit separator so field boundaries can't be confused
    return h.hexdigest()


def dedup_key(
    source_name: str, url: str, title: str, published_at: datetime | None
) -> str:
    """Identity hash used for idempotent persistence (UNIQUE in SQLite)."""
    published = published_at.isoformat() if published_at else ""
    # URL is identity-critical and kept verbatim (only stripped) — never normalised away.
    return _sha256(_normalize(source_name), url.strip(), _normalize(title), published)


def content_hash(title: str, summary: str | None) -> str:
    """Content fingerprint used for stage-(a) exact-content dedup."""
    return _sha256(_normalize(title), _normalize(summary))


def embedding_text(title: str, summary: str | None) -> str:
    """The text handed to the embedder for one item (title + summary)."""
    summary = summary or ""
    return f"{title.strip()}\n{summary.strip()}".strip()
