"""Tests for GET /sources (Task 002 / M1).

Runs against the real configured registry (`sources/sources.yaml`); asserts shape and the
`enabled` filter without hard-coding brittle counts.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_sources_returns_configured_sources():
    resp = client.get("/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    first = body[0]
    # Fields present and URL preserved.
    assert {"name", "source_type", "url", "enabled", "trust_level"} <= set(first)
    assert all(s["url"] for s in body)


def test_enabled_filter_partitions_the_registry():
    all_sources = client.get("/sources").json()
    enabled = client.get("/sources", params={"enabled": "true"}).json()
    disabled = client.get("/sources", params={"enabled": "false"}).json()

    assert all(s["enabled"] is True for s in enabled)
    assert all(s["enabled"] is False for s in disabled)
    assert len(enabled) + len(disabled) == len(all_sources)


def test_known_source_types_only():
    body = client.get("/sources").json()
    allowed = {
        "rss",
        "github_releases",
        "arxiv",
        "github_star_velocity",
        "github_new_repos",
        "github_advisories",
        "github_changes",
    }
    assert {s["source_type"] for s in body} <= allowed
