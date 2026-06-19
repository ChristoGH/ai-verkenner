"""Tests for the source registry model + loader (Task 002 / M1)."""

from pathlib import Path

from app.schemas.source import SourceType, TrustLevel
from app.sources.registry import load_sources

FIXTURES = Path(__file__).parent / "fixtures"


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "sources.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_valid_fixture_parses_all_entries():
    result = load_sources(FIXTURES / "sources_valid.yaml")
    assert result.ok
    assert result.errors == []
    assert len(result.sources) == 4
    names = {s.name for s in result.sources}
    assert "Example RSS" in names
    # The curated GitHub-intelligence type validates even though its fetcher is a stub.
    assert any(s.source_type is SourceType.github_new_repos for s in result.sources)
    rss = next(s for s in result.sources if s.name == "Example RSS")
    assert rss.trust_level is TrustLevel.high
    assert rss.url == "https://example.com/feed.xml"  # preserved verbatim


def test_rejects_bad_source_type(tmp_path):
    path = _write(
        tmp_path,
        "sources:\n"
        "  - name: Bad type\n"
        "    source_type: not_a_real_type\n"
        "    url: https://example.com/feed.xml\n"
        "    enabled: true\n"
        "    trust_level: high\n",
    )
    result = load_sources(path)
    assert result.sources == []
    assert len(result.errors) == 1
    assert "source_type" in result.errors[0].reason
    assert "Bad type" in result.errors[0].entry  # the name is in the pointer


def test_rejects_missing_url(tmp_path):
    path = _write(
        tmp_path,
        "sources:\n"
        "  - name: No URL\n"
        "    source_type: rss\n"
        "    enabled: true\n"
        "    trust_level: high\n",
    )
    result = load_sources(path)
    assert result.sources == []
    assert len(result.errors) == 1
    assert "url" in result.errors[0].reason


def test_rejects_bad_trust_level(tmp_path):
    path = _write(
        tmp_path,
        "sources:\n"
        "  - name: Bad trust\n"
        "    source_type: rss\n"
        "    url: https://example.com/feed.xml\n"
        "    enabled: true\n"
        "    trust_level: superb\n",
    )
    result = load_sources(path)
    assert result.sources == []
    assert len(result.errors) == 1
    assert "trust_level" in result.errors[0].reason


def test_one_bad_entry_does_not_drop_the_good_ones(tmp_path):
    path = _write(
        tmp_path,
        "sources:\n"
        "  - name: Good\n"
        "    source_type: rss\n"
        "    url: https://example.com/feed.xml\n"
        "    enabled: true\n"
        "    trust_level: high\n"
        "  - name: Bad\n"
        "    source_type: rss\n"
        "    enabled: true\n"
        "    trust_level: high\n",
    )
    result = load_sources(path)
    assert [s.name for s in result.sources] == ["Good"]
    assert len(result.errors) == 1


def test_github_releases_requires_repo_fields(tmp_path):
    path = _write(
        tmp_path,
        "sources:\n"
        "  - name: Releases without repo\n"
        "    source_type: github_releases\n"
        "    url: https://github.com/example/repo/releases\n"
        "    enabled: true\n"
        "    trust_level: high\n",
    )
    result = load_sources(path)
    assert result.sources == []
    assert "repo_owner" in result.errors[0].reason


def test_missing_file_reports_not_found_without_crashing(tmp_path):
    result = load_sources(tmp_path / "does_not_exist.yaml")
    assert result.sources == []
    assert len(result.errors) == 1
    assert "not found" in result.errors[0].reason


def test_malformed_yaml_is_reported_without_crashing(tmp_path):
    path = _write(tmp_path, "sources:\n  - name: x\n  bad: : : :\n")
    result = load_sources(path)
    assert result.sources == []
    assert any("YAML" in e.reason for e in result.errors)


def test_wrong_top_level_shape_is_reported(tmp_path):
    path = _write(tmp_path, "just_a_string\n")
    result = load_sources(path)
    assert result.sources == []
    assert "sources" in result.errors[0].reason


def test_unknown_field_is_rejected(tmp_path):
    path = _write(
        tmp_path,
        "sources:\n"
        "  - name: Typo field\n"
        "    source_type: rss\n"
        "    url: https://example.com/feed.xml\n"
        "    enabled: true\n"
        "    trust_level: high\n"
        "    trust_levle: high\n",  # typo
    )
    result = load_sources(path)
    assert result.sources == []
    assert len(result.errors) == 1
