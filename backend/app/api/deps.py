"""Shared FastAPI dependencies for the dashboard routers (M6).

`session` yields a SQLite session on the process engine. `graph_store` returns a live
`Neo4jGraphStore` when Neo4j is reachable, or `None` when it is down — every dashboard endpoint
degrades cleanly to a graph-less result rather than failing. Tests override both dependencies to
inject an in-memory session and an `InMemoryGraph` (or `None`), so the suite needs no live stores.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlmodel import Session

from app.db import neo4j
from app.db.sqlite import get_session, init_db
from app.graph import GraphStore, Neo4jGraphStore

logger = logging.getLogger(__name__)


def session_dep() -> Iterator[Session]:
    """Yield a SQLite session (tables ensured)."""
    init_db()
    with get_session() as session:
        yield session


def graph_store_dep() -> GraphStore | None:
    """Return a live graph store, or None if Neo4j is unreachable (degrade-don't-crash)."""
    status = neo4j.ping()
    if not status.ok:
        logger.info("graph store unavailable (%s); dashboard degrades to graph-less", status.detail)
        return None
    return Neo4jGraphStore(neo4j.get_driver())
