"""Database / store clients.

At milestone **M2** this package provides thin connectivity wrappers for the two derived stores
adopted by ADR 0001 — Qdrant (vectors) and Neo4j (graph) — plus a shared `DependencyStatus`.

Connectivity only: no schemas, collections, tables, or writes (those are M3+). Every `ping()`
**degrades rather than raises** — a store being down must never crash the app, because SQLite is
the source of truth and these stores are rebuildable derived indices (CLAUDE.md invariant).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DependencyState = Literal["ok", "unreachable"]


@dataclass(frozen=True)
class DependencyStatus:
    """The reachability of one external store, safe to serialise into /health."""

    name: str
    status: DependencyState
    detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


__all__ = ["DependencyStatus", "DependencyState"]
