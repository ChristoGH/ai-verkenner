"""M7.5 post generator — offline, deterministic, $0 (no LLM, no stores, no network).

Drives `app.posts.generate_posts` over the two fixture Digests and asserts the milestone's contract:
per-surface shape, URL preservation, FACT vs INTERPRETATION separation, honest Noise Report, a real
Weak Signal of the Week on convergence and a graceful degrade without it — and that no social-posting
code path exists anywhere in `app.posts`.
"""

from __future__ import annotations

from pathlib import Path

from app.posts import (
    PIECE_NOISE_REPORT,
    PIECE_WEAK_SIGNAL,
    SURFACE_LINKEDIN,
    SURFACE_MEDIUM,
    SURFACE_X,
    generate_posts,
)
from app.posts.model import FACT_LABEL, INTERP_LABEL, METHOD_LABEL, X_CHAR_LIMIT
from tests.posts_fixtures import converging_digest, thin_digest


def _bullet_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("- "))


def _one(bundle, surface, piece):
    matches = [d for d in bundle.drafts if d.surface == surface and d.piece == piece]
    assert len(matches) == 1, f"expected exactly one {surface}/{piece} draft"
    return matches[0]


# ---- bundle shape ----


def test_bundle_has_six_drafts_two_pieces_three_surfaces():
    bundle = generate_posts(converging_digest(), digest_id=7)
    assert len(bundle.drafts) == 6
    assert {d.surface for d in bundle.drafts} == {SURFACE_X, SURFACE_LINKEDIN, SURFACE_MEDIUM}
    assert {d.piece for d in bundle.drafts} == {PIECE_WEAK_SIGNAL, PIECE_NOISE_REPORT}
    assert bundle.digest_id == 7


def test_every_draft_marks_itself_a_draft_no_autopost():
    for fixture in (converging_digest(), thin_digest()):
        for d in generate_posts(fixture).drafts:
            assert "DRAFT" in d.text
            assert "NOT auto-posted" in d.text


# ---- X (Twitter) ----


def test_x_hook_within_limit_with_link_both_pieces():
    bundle = generate_posts(converging_digest())
    for piece in (PIECE_WEAK_SIGNAL, PIECE_NOISE_REPORT):
        d = _one(bundle, SURFACE_X, piece)
        assert len(d.hook) <= X_CHAR_LIMIT, f"{piece} hook is {len(d.hook)} chars"
        assert "http" in d.hook, f"{piece} hook must carry an evidence link"


def test_x_hook_stays_within_limit_even_with_a_very_long_title():
    data = converging_digest()
    long_title = "Extremely long headline " * 30
    lead = data.weak_signals[0]
    weak = (type(lead)(**{**lead.__dict__, "title": long_title}),) + data.weak_signals[1:]
    data = type(data)(**{**data.__dict__, "weak_signals": weak})
    d = _one(generate_posts(data), SURFACE_X, PIECE_WEAK_SIGNAL)
    assert len(d.hook) <= X_CHAR_LIMIT
    assert "http" in d.hook  # the evidence link survives the trim


# ---- LinkedIn ----


def test_linkedin_has_hook_three_bullets_and_cta():
    bundle = generate_posts(converging_digest())
    for piece in (PIECE_WEAK_SIGNAL, PIECE_NOISE_REPORT):
        d = _one(bundle, SURFACE_LINKEDIN, piece)
        assert d.hook and d.text.count(d.hook) >= 1
        assert _bullet_count(d.text) == 3, f"{piece} LinkedIn should have exactly 3 bullets"
        assert "CTA:" in d.text


def test_linkedin_keeps_three_bullets_on_a_thin_digest():
    d = _one(generate_posts(thin_digest()), SURFACE_LINKEDIN, PIECE_WEAK_SIGNAL)
    assert _bullet_count(d.text) == 3  # padded honestly when fewer than 3 items


# ---- Medium ----


def test_medium_has_narrative_evidence_links_and_methodology():
    bundle = generate_posts(converging_digest())
    for piece in (PIECE_WEAK_SIGNAL, PIECE_NOISE_REPORT):
        d = _one(bundle, SURFACE_MEDIUM, piece)
        assert d.text.startswith("<!--") and "# " in d.text          # long-form narrative
        assert "## Evidence" in d.text
        assert f"## {METHOD_LABEL}" in d.text
        for url in d.source_urls:
            assert url in d.text                                     # every source URL preserved


# ---- Weak Signal of the Week: convergence vs graceful degrade ----


def test_convergence_fixture_produces_a_real_weak_signal():
    bundle = generate_posts(converging_digest())
    assert bundle.has_convergence is True
    x = _one(bundle, SURFACE_X, PIECE_WEAK_SIGNAL)
    assert "converging" in x.text.lower()
    assert "independent sources" in x.text.lower()
    medium = _one(bundle, SURFACE_MEDIUM, PIECE_WEAK_SIGNAL)
    # Names the three independent publishers behind the convergence.
    for pub in ("VentureBeat", "The Register", "arXiv"):
        assert pub in medium.text


def test_thin_fixture_degrades_without_false_convergence_claim():
    bundle = generate_posts(thin_digest())
    assert bundle.has_convergence is False
    for surface in (SURFACE_X, SURFACE_LINKEDIN, SURFACE_MEDIUM):
        d = _one(bundle, surface, PIECE_WEAK_SIGNAL)
        assert "converging" not in d.text.lower(), f"{surface} falsely claims convergence"


# ---- invariants: URLs preserved + FACT vs INTERPRETATION ----


def test_every_draft_preserves_its_source_urls():
    for fixture in (converging_digest(), thin_digest()):
        for d in generate_posts(fixture).drafts:
            assert d.source_urls, f"{d.slug} lost its source URLs"
            for url in d.source_urls:
                assert url in d.text


def test_drafts_separate_fact_from_interpretation():
    for fixture in (converging_digest(), thin_digest()):
        for d in generate_posts(fixture).drafts:
            assert FACT_LABEL in d.text, f"{d.slug} missing a FACT label"
            assert INTERP_LABEL in d.text, f"{d.slug} missing an interpretation label"


# ---- Noise Report: honest, loudest-but-emptiest ----


def test_noise_report_lists_high_hype_and_archive_items_loudest_first():
    bundle = generate_posts(converging_digest())
    x = _one(bundle, SURFACE_X, PIECE_NOISE_REPORT)
    # The loud (hype 5) item leads; both demotions' URLs are preserved.
    assert "hype 5/5" in x.text
    assert "https://hypedaily.example/agi-now" in x.text
    assert "https://linkfarm.example/roundup-201" in x.text
    # Loudest first: the hype-5 story appears before the archived one in the thread.
    assert x.text.index("hypedaily") < x.text.index("linkfarm")


def test_noise_report_medium_names_items_and_keeps_evidence():
    d = _one(generate_posts(converging_digest()), SURFACE_MEDIUM, PIECE_NOISE_REPORT)
    assert "archived" in d.text.lower()
    for url in ("https://hypedaily.example/agi-now", "https://linkfarm.example/roundup-201"):
        assert url in d.text


# ---- the hard guardrail: no social-posting code path exists ----


def test_no_social_posting_or_network_code_path_in_app_posts():
    posts_dir = Path(__file__).resolve().parents[1] / "app" / "posts"
    forbidden = (
        "tweepy", "selenium", "playwright", "webbrowser", "smtplib",
        "oauth", "access_token", "bearer_token", "api.twitter.com", "api.linkedin.com",
        "import requests", "from requests", "import httpx", "from httpx",
        "import urllib", "http.client", "socket.socket",
    )
    for path in posts_dir.glob("*.py"):
        src = path.read_text().lower()
        for token in forbidden:
            assert token.lower() not in src, f"{path.name} contains forbidden token: {token!r}"
