"""Tests for the curated github_* fetchers + recency cap (M6.5).

Offline + deterministic: GitHub API payloads are fixtures, no live network. Covers parsing for each
type, honest star-velocity (delta from two snapshots; baseline emits nothing), the recency cap, and
clean token-absent skipping.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from app.core import config as config_module
from app.db.sqlite import init_db, make_engine
from app.ingestion.fetchers import github_intelligence as gi
from app.ingestion.orchestrator import apply_recency_cap
from app.ingestion.star_velocity_store import latest_snapshots, record_snapshots
from app.models import RepoStarSnapshot
from app.schemas.raw_item import RawItem
from app.schemas.source import Source, SourceType, TrustLevel

NOW = datetime(2026, 6, 20, tzinfo=timezone.utc)


def _source(source_type: SourceType, **kwargs) -> Source:
    base = dict(name="GH", source_type=source_type, url="https://github.com/x",
                trust_level=TrustLevel.medium)
    base.update(kwargs)
    return Source(**base)


# ---- github_new_repos ----


def test_parse_repo_search_preserves_urls_and_dates():
    payload = {"items": [
        {"full_name": "openai/whisper", "html_url": "https://github.com/openai/whisper",
         "created_at": "2026-06-18T10:00:00Z", "description": "ASR"},
        {"full_name": "a/b", "html_url": "https://github.com/a/b", "created_at": None,
         "description": None},
    ]}
    src = _source(SourceType.github_new_repos, github_topic="llm")
    items = gi.parse_repo_search(payload, src, title_prefix="New repo")
    assert [i.title for i in items] == ["New repo: openai/whisper", "New repo: a/b"]
    assert items[0].url == "https://github.com/openai/whisper"
    assert items[0].published_at is not None
    assert all(i.url for i in items)  # every item keeps a URL


def test_new_repos_query_uses_topic_or_owner():
    topic_src = _source(SourceType.github_new_repos, github_topic="rag")
    owner_src = _source(SourceType.github_new_repos, repo_owner="anthropics")
    assert gi.new_repos_query(topic_src, "2026-06-01") == "topic:rag created:>=2026-06-01"
    assert gi.new_repos_query(owner_src, "2026-06-01") == "user:anthropics created:>=2026-06-01"


# ---- github_star_velocity (honest delta) ----


def test_star_velocity_baseline_emits_nothing_then_delta():
    src = _source(SourceType.github_star_velocity, github_topic="rag")
    repos = [
        {"full_name": "a/rag", "html_url": "https://github.com/a/rag",
         "stargazers_count": 100, "description": "rag lib"},
        {"full_name": "b/vec", "html_url": "https://github.com/b/vec",
         "stargazers_count": 50, "description": None},
    ]
    # First run: no previous snapshot → baseline, emit nothing.
    assert gi.compute_star_velocity(repos, {}, src, now=NOW) == []
    # Second run: stars grew → only positive deltas surface.
    previous = {"a/rag": 80, "b/vec": 50}  # a/rag +20, b/vec unchanged
    items = gi.compute_star_velocity(repos, previous, src, now=NOW)
    assert len(items) == 1
    assert "a/rag gained 20 stars (now 100)" == items[0].title
    assert items[0].url == "https://github.com/a/rag"


def test_star_velocity_ignores_decreases():
    src = _source(SourceType.github_star_velocity, github_topic="rag")
    repos = [{"full_name": "a/b", "html_url": "https://github.com/a/b", "stargazers_count": 5}]
    assert gi.compute_star_velocity(repos, {"a/b": 9}, src, now=NOW) == []


def test_star_snapshot_store_roundtrip():
    eng = make_engine("sqlite://")
    init_db(eng)
    with Session(eng) as s:
        assert latest_snapshots(s, ["a/b"]) == {}
        record_snapshots(s, {"a/b": 80, "c/d": 10}, captured_at=NOW - timedelta(days=1))
        record_snapshots(s, {"a/b": 100}, captured_at=NOW)  # newer snapshot wins
        assert latest_snapshots(s, ["a/b", "c/d"]) == {"a/b": 100, "c/d": 10}
        assert len(s.exec(select(RepoStarSnapshot)).all()) == 3


# ---- github_advisories ----


def test_parse_advisories_preserves_url_and_severity():
    payload = [{
        "ghsa_id": "GHSA-xxxx", "summary": "RCE in foo", "html_url": "https://github.com/advisories/GHSA-xxxx",
        "published_at": "2026-06-19T00:00:00Z", "severity": "critical", "description": "details",
    }]
    src = _source(SourceType.github_advisories, github_package="fastapi", github_ecosystem="pip")
    items = gi.parse_advisories(payload, src)
    assert items[0].url == "https://github.com/advisories/GHSA-xxxx"
    assert "GHSA-xxxx" in items[0].title
    assert "severity: critical" in items[0].summary


# ---- github_changes ----


def test_parse_issues_marks_prs_and_keeps_urls():
    payload = [
        {"title": "Deprecate old API", "html_url": "https://github.com/o/r/issues/1",
         "created_at": "2026-06-18T00:00:00Z", "body": "breaking"},
        {"title": "Remove flag", "html_url": "https://github.com/o/r/pull/2",
         "created_at": "2026-06-17T00:00:00Z", "body": "", "pull_request": {"url": "..."}},
    ]
    src = _source(SourceType.github_changes, repo_owner="o", repo_name="r")
    items = gi.parse_issues(payload, src)
    assert items[0].title.startswith("[issue] ")
    assert items[1].title.startswith("[PR] ")
    assert items[1].url == "https://github.com/o/r/pull/2"


# ---- token-absent skip ----


@pytest.mark.parametrize("fetcher,kwargs", [
    (gi.fetch_github_new_repos, {"github_topic": "llm"}),
    (gi.fetch_github_star_velocity, {"github_topic": "rag"}),
    (gi.fetch_github_advisories, {"github_package": "fastapi"}),
    (gi.fetch_github_changes, {"repo_owner": "o", "repo_name": "r"}),
])
def test_github_fetchers_skip_cleanly_without_token(fetcher, kwargs, monkeypatch):
    monkeypatch.setattr(config_module.settings, "github_token", None)
    st = {
        "fetch_github_new_repos": SourceType.github_new_repos,
        "fetch_github_star_velocity": SourceType.github_star_velocity,
        "fetch_github_advisories": SourceType.github_advisories,
        "fetch_github_changes": SourceType.github_changes,
    }[fetcher.__name__]
    src = _source(st, **kwargs)
    assert fetcher(src) == []  # no token → skip, no crash, no network


# ---- recency cap ----


def test_recency_cap_bounds_oversized_feed():
    items = [RawItem(source_name="HF", source_type=SourceType.rss, title=f"t{i}",
                     url=f"https://hf/{i}", published_at=NOW - timedelta(days=i)) for i in range(200)]
    capped = apply_recency_cap(items, max_age_days=14, max_items=10, now=NOW)
    assert len(capped) == 10                       # ceiling honoured
    assert all((NOW - it.published_at).days <= 14 for it in capped)  # window honoured
    # Newest kept.
    assert capped[0].title == "t0"


def test_recency_cap_keeps_undated_items_under_ceiling():
    items = [RawItem(source_name="S", source_type=SourceType.rss, title="undated", url="https://x/u")]
    capped = apply_recency_cap(items, max_age_days=30, max_items=40, now=NOW)
    assert len(capped) == 1  # undated items are kept (can't judge age)
