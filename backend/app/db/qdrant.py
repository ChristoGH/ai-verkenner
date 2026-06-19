"""Thin Qdrant client wrapper (M2 — connectivity only).

Exposes a lazily-created `QdrantClient` and a `ping()` that reports reachability **without
raising**. No collections, no vectors, no writes — those land in M3.
"""

from __future__ import annotations

import logging

from qdrant_client import QdrantClient

from app.core.config import settings
from app.db import DependencyStatus

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    """Return a process-wide Qdrant client (created on first use).

    Construction does not open a connection; the first real call (e.g. in `ping`) does.
    """
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url, timeout=int(settings.store_ping_timeout))
    return _client


def ping() -> DependencyStatus:
    """Report whether Qdrant is reachable. Never raises — degrades to 'unreachable'."""
    try:
        # Cheapest authenticated round-trip that proves the server answers.
        get_client().get_collections()
        return DependencyStatus("qdrant", "ok")
    except Exception as exc:  # noqa: BLE001 — degrade-don't-crash is the whole point here
        logger.warning("qdrant unreachable at %s: %s", settings.qdrant_url, exc)
        return DependencyStatus("qdrant", "unreachable", f"{type(exc).__name__}: {exc}")


def close() -> None:
    """Best-effort client close for app shutdown."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:  # noqa: BLE001 — shutdown must not raise
            pass
        _client = None
