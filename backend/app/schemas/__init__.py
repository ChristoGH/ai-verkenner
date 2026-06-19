"""Pydantic schemas for AI Verkenner.

These are in-memory request/response and pipeline shapes (validated with Pydantic). They are
deliberately separate from `app.models`, which will hold the SQLModel/SQLAlchemy persistence
entities once SQLite arrives (Task 004 / milestone M3). At M1 nothing is persisted.
"""

from app.schemas.raw_item import RawItem
from app.schemas.source import Source, SourceType, TrustLevel

__all__ = ["Source", "SourceType", "TrustLevel", "RawItem"]
