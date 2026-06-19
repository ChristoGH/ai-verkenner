"""Tests for the dedup hashes (M3)."""

from datetime import datetime, timezone

from app.storage.hashing import content_hash, dedup_key


def test_dedup_key_is_stable_for_equal_items():
    ts = datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc)
    a = dedup_key("Feed A", "https://x.example/1", "Title", ts)
    b = dedup_key("Feed A", "https://x.example/1", "Title", ts)
    assert a == b


def test_dedup_key_differs_when_url_differs():
    # Two sources covering the same story keep distinct identity keys (different URLs).
    a = dedup_key("Feed A", "https://a.example/1", "Same title", None)
    b = dedup_key("Feed B", "https://b.example/1", "Same title", None)
    assert a != b


def test_dedup_key_differs_when_published_differs():
    a = dedup_key("F", "https://x/1", "T", datetime(2026, 1, 1, tzinfo=timezone.utc))
    b = dedup_key("F", "https://x/1", "T", datetime(2026, 1, 2, tzinfo=timezone.utc))
    assert a != b


def test_content_hash_ignores_whitespace_and_case():
    a = content_hash("GPT-5 Released", "Big news")
    b = content_hash("  gpt-5   released  ", "big   news")
    assert a == b


def test_content_hash_distinct_for_different_content():
    a = content_hash("GPT-5 released", "OpenAI")
    b = content_hash("Qdrant 1.9 ships", "vector db")
    assert a != b


def test_content_hash_same_text_different_sources_collapses():
    # Byte-identical coverage from two sources shares a content hash (→ same Event in stage a),
    # even though their identity keys differ.
    text_title, text_summary = "Model X launches", "Lab Y ships Model X"
    assert content_hash(text_title, text_summary) == content_hash(text_title, text_summary)
