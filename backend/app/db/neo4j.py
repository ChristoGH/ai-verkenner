"""Thin Neo4j driver wrapper (M2 — connectivity only).

Exposes a lazily-created driver and a `ping()` that reports reachability **without raising**. No
graph schema, no nodes, no edges, no writes — those land in M5.
"""

from __future__ import annotations

import logging

from neo4j import Driver, GraphDatabase

from app.core.config import settings
from app.db import DependencyStatus

logger = logging.getLogger(__name__)

_driver: Driver | None = None


def get_driver() -> Driver:
    """Return a process-wide Neo4j driver (created on first use).

    Creating the driver does not connect; `verify_connectivity` (in `ping`) does. A short
    connection timeout keeps health checks snappy when the database is down.
    """
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=settings.store_ping_timeout,
            connection_acquisition_timeout=settings.store_ping_timeout,
            max_transaction_retry_time=settings.store_ping_timeout,
        )
    return _driver


def ping() -> DependencyStatus:
    """Report whether Neo4j is reachable. Never raises — degrades to 'unreachable'."""
    try:
        get_driver().verify_connectivity()
        return DependencyStatus("neo4j", "ok")
    except Exception as exc:  # noqa: BLE001 — degrade-don't-crash is the whole point here
        logger.warning("neo4j unreachable at %s: %s", settings.neo4j_uri, exc)
        return DependencyStatus("neo4j", "unreachable", f"{type(exc).__name__}: {exc}")


def close() -> None:
    """Best-effort driver close for app shutdown."""
    global _driver
    if _driver is not None:
        try:
            _driver.close()
        except Exception:  # noqa: BLE001 — shutdown must not raise
            pass
        _driver = None
