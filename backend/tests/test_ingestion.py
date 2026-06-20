"""Tests for ingestion fetchers + orchestrator (Task 003 / M1).

No network is touched: parse functions run on fixtures and the orchestrator runs against injected
fetchers.
"""

import json
from pathlib import Path

from app.ingestion.fetchers.arxiv import build_arxiv_url, parse_arxiv
from app.ingestion.fetchers.github_releases import parse_github_releases, releases_url
from app.ingestion.fetchers.rss import parse_rss
from app.ingestion.orchestrator import run_ingestion
from app.schemas.source import Source, SourceType

FIXTURES = Path(__file__).parent / "fixtures"


def _source(**kwargs) -> Source:
    base = dict(
        name="S",
        source_type=SourceType.rss,
        url="https://example.com/feed.xml",
        enabled=True,
        trust_level="high",
    )
    base.update(kwargs)
    return Source(**base)


# ---- RSS parsing ----


def test_parse_rss_fixture():
    content = (FIXTURES / "rss_sample.xml").read_bytes()
    source = _source(name="Example RSS")
    items = parse_rss(content, source)
    assert len(items) == 2
    first = items[0]
    assert first.title == "First post"
    assert first.url == "https://example.com/posts/first"  # link preserved
    assert first.source_name == "Example RSS"
    assert first.published_at is not None
    # Every item keeps a URL.
    assert all(item.url for item in items)


# ---- GitHub releases parsing ----


def test_parse_github_releases_fixture():
    payload = json.loads((FIXTURES / "github_releases.json").read_text())
    source = _source(
        name="Example Releases",
        source_type=SourceType.github_releases,
        url="https://github.com/example/repo/releases",
        repo_owner="example",
        repo_name="repo",
    )
    items = parse_github_releases(payload, source)
    assert len(items) == 2
    assert items[0].title == "v1.2.0"
    assert items[0].url == "https://github.com/example/repo/releases/tag/v1.2.0"
    # When name is blank, fall back to tag_name.
    assert items[1].title == "v1.1.0"
    assert all(item.url for item in items)


def test_github_releases_url_builder():
    source = _source(
        source_type=SourceType.github_releases,
        url="https://github.com/example/repo/releases",
        repo_owner="example",
        repo_name="repo",
    )
    assert releases_url(source) == "https://api.github.com/repos/example/repo/releases"


# ---- arXiv URL builder ----


def test_build_arxiv_url():
    source = _source(
        source_type=SourceType.arxiv,
        url="https://arxiv.org/list/cs.AI/recent",
        arxiv_query="cat:cs.AI",
    )
    url = build_arxiv_url(source, max_results=5)
    assert url.startswith("http://export.arxiv.org/api/query?")
    assert "search_query=cat%3Acs.AI" in url
    assert "max_results=5" in url
    assert "sortBy=submittedDate" in url


def test_parse_arxiv_atom_minimal():
    atom = b"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>A paper about\n   convergence</title>
        <link href="http://arxiv.org/abs/2606.00001v1"/>
        <summary>We study convergence.</summary>
        <published>2026-06-15T00:00:00Z</published>
      </entry>
    </feed>"""
    source = _source(source_type=SourceType.arxiv, arxiv_query="cat:cs.AI")
    items = parse_arxiv(atom, source)
    assert len(items) == 1
    assert items[0].title == "A paper about convergence"  # whitespace collapsed
    assert items[0].url == "http://arxiv.org/abs/2606.00001v1"


# ---- Orchestrator: per-source failure isolation ----


def test_orchestrator_isolates_a_broken_source():
    # The good source is rss; the broken one is arxiv, so each routes to its own injected fetcher.
    good = _source(name="Good", url="https://good.example/feed.xml")
    broken = _source(
        name="Broken",
        source_type=SourceType.arxiv,
        url="https://broken.example/feed.xml",
        arxiv_query="cat:cs.AI",
    )

    def good_fetcher(src):
        return parse_rss((FIXTURES / "rss_sample.xml").read_bytes(), src)

    def broken_fetcher(src):
        raise RuntimeError("boom: simulated network/parse failure")

    fetchers = {SourceType.rss: good_fetcher, SourceType.arxiv: broken_fetcher}
    run = run_ingestion([good, broken], fetchers=fetchers)

    # The good items came through.
    assert len(run.items) == 2
    assert all(item.source_name == "Good" for item in run.items)
    # The failure is reported, not raised.
    assert len(run.failed) == 1
    assert run.failed[0].source_name == "Broken"
    assert "boom" in run.failed[0].error
    assert len(run.succeeded) == 1
    assert run.succeeded[0].item_count == 2


def test_orchestrator_skips_disabled_sources():
    enabled = _source(name="On", url="https://on.example/feed.xml")
    disabled = _source(name="Off", url="https://off.example/feed.xml", enabled=False)

    def fetcher(src):
        return parse_rss((FIXTURES / "rss_sample.xml").read_bytes(), src)

    run = run_ingestion([enabled, disabled], fetchers={SourceType.rss: fetcher})
    assert {r.source_name for r in run.results} == {"On"}


def test_orchestrator_skips_github_sources_without_token(monkeypatch):
    """Without GITHUB_TOKEN, a github_* source degrades to zero items through the real registry."""
    from app.core import config as config_module

    monkeypatch.setattr(config_module.settings, "github_token", None)
    source = _source(
        name="Watched repos",
        source_type=SourceType.github_new_repos,
        url="https://github.com/topics/llm",
        github_topic="llm",
    )
    run = run_ingestion([source], max_age_days=0, max_items=0)  # uses the real FETCHERS map
    assert run.items == []
    assert len(run.succeeded) == 1
    assert run.succeeded[0].item_count == 0
