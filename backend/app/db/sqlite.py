"""SQLite engine + session helpers (M3) — the system of record.

The engine is injectable: the app/CLI use the process-wide engine built from `DATABASE_URL`, while
tests build their own (a temp file or in-memory DB). Importing this module has no side effects;
call `init_db(engine)` to create tables.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Import so the models register on SQLModel.metadata before create_all.
from app import models  # noqa: F401
from app.core.config import settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None


def _ensure_sqlite_dir(database_url: str) -> None:
    """Create the parent directory for a sqlite file URL so the engine can open it."""
    prefix = "sqlite:///"
    if database_url.startswith(prefix):
        path = database_url[len(prefix):]
        if path and path != ":memory:":
            Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def make_engine(database_url: str | None = None) -> Engine:
    """Build a SQLAlchemy engine for the given (or configured) SQLite URL."""
    url = database_url or settings.database_url
    connect_args = {}
    engine_kwargs: dict = {}
    if url.startswith("sqlite"):
        # SQLite + threaded server: allow cross-thread use.
        connect_args["check_same_thread"] = False
        # An in-memory DB lives only as long as its connection — pin one shared connection so the
        # schema survives across sessions ("sqlite://" and "sqlite:///:memory:" are both memory).
        is_memory = url in ("sqlite://", "sqlite:///:memory:") or ":memory:" in url
        if is_memory:
            engine_kwargs["poolclass"] = StaticPool
        else:
            _ensure_sqlite_dir(url)
    return create_engine(url, connect_args=connect_args, **engine_kwargs)


def get_engine() -> Engine:
    """Return the process-wide engine (created on first use)."""
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def init_db(engine: Engine | None = None) -> Engine:
    """Create all tables. Idempotent — safe to call on every startup/run."""
    engine = engine or get_engine()
    SQLModel.metadata.create_all(engine)
    return engine


def get_session(engine: Engine | None = None) -> Session:
    """Open a new session on the given (or process-wide) engine."""
    return Session(engine or get_engine())
