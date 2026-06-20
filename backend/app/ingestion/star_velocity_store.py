"""Persistence for honest star-velocity tracking (M6.5).

`github_star_velocity` does NOT fake a rate from absolute stars. Each run snapshots a watched
repo's star count to SQLite; the *velocity* is the delta against the previous snapshot. These
helpers read the latest prior snapshot and record the new one — the fetcher wires the GitHub API
around them.
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from app.models import RepoStarSnapshot


def latest_snapshots(session: Session, repo_names: list[str]) -> dict[str, int]:
    """The most recent star count recorded for each given repo (empty if never seen)."""
    out: dict[str, int] = {}
    for name in repo_names:
        row = session.exec(
            select(RepoStarSnapshot)
            .where(RepoStarSnapshot.repo_full_name == name)
            .order_by(RepoStarSnapshot.captured_at.desc(), RepoStarSnapshot.id.desc())
        ).first()
        if row is not None:
            out[name] = row.stars
    return out


def record_snapshots(
    session: Session, repo_stars: dict[str, int], *, captured_at: datetime | None = None
) -> None:
    """Persist this run's star counts as the new baseline for next run's delta."""
    for name, stars in repo_stars.items():
        snap = RepoStarSnapshot(repo_full_name=name, stars=stars)
        if captured_at is not None:
            snap.captured_at = captured_at
        session.add(snap)
    session.commit()
