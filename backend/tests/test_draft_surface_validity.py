"""Task 010 Defects 2 + 3 — every generated draft must be valid on the surface it targets.

Offline and deterministic (no DB, no graph store, no LLM): drives the real
`posts.generate_posts` path over fixtures sized like the real corpus.

The two regressions pinned here, both from the M7.5 run (2026-07-21):

* **Defect 2** — only the X *hook* went through the fitter; thread items were emitted unchecked and
  ran 400–800 characters against a 280 limit. The related finding D-025 showed the hook itself was
  no better off: a 162-character source URL left ~2 characters for the label, so a 6-character
  entity name rendered as `Op…`.
* **Defect 3** — the Noise Report had no editorial cap: 187 items, a 141 KB Medium draft and 16 KB
  X / LinkedIn variants.
"""

from __future__ import annotations

import re

import pytest

from app.core.config import settings
from app.posts import (
    PIECE_NOISE_REPORT,
    PIECE_WEAK_SIGNAL,
    SURFACE_LINKEDIN,
    SURFACE_MEDIUM,
    SURFACE_X,
    generate_posts,
)
from app.posts.model import FACT_LABEL, X_CHAR_LIMIT
from tests.posts_fixtures import (
    converging_digest,
    long_form_digest,
    noisy_digest,
    thin_digest,
)

# A numbered post in an X thread ("2/ FACT: …"). The reference "Sources:" block at the foot of the
# draft is deliberately NOT one — it is a list for the human assembling the thread, not a post.
_THREAD_ITEM = re.compile(r"^\d+/ ")


def _one(bundle, surface, piece):
    return next(d for d in bundle.drafts if d.surface == surface and d.piece == piece)


def _x_posts(draft) -> list[str]:
    """Every string in an X draft that is meant to be POSTED: the hook plus the thread items."""
    return [draft.hook] + [
        line for line in draft.text.splitlines() if _THREAD_ITEM.match(line)
    ]


def _fact_lines(draft) -> list[str]:
    """The lines that NAME an item on any surface (one per item, on all three)."""
    return [
        line for line in draft.text.splitlines()
        if line.lstrip().startswith(("-", "1", "2", "3", "4", "5", "6", "7", "8", "9"))
        and f"{FACT_LABEL}:" in line
    ]


# ---- Defect 2: the X surface ----


@pytest.mark.parametrize(
    "fixture", [thin_digest, converging_digest, long_form_digest, noisy_digest],
    ids=["thin", "converging", "long-form", "noisy"],
)
@pytest.mark.parametrize("piece", [PIECE_WEAK_SIGNAL, PIECE_NOISE_REPORT])
def test_all_x_thread_items_within_limit(fixture, piece):
    """Every posted X string — hook AND thread item — fits the limit, on every fixture shape."""
    draft = _one(generate_posts(fixture()), SURFACE_X, piece)
    posts = _x_posts(draft)
    assert posts, "the X draft emitted nothing to post"
    for post in posts:
        assert len(post) <= X_CHAR_LIMIT, (
            f"{piece} X post is {len(post)} chars (limit {X_CHAR_LIMIT}): {post[:120]!r}"
        )


def test_x_truncation_preserves_urls():
    """Trimming may cost prose; it may never cost a link. The URL set is unchanged after fitting."""
    data = long_form_digest()
    expected = tuple(it.source_url for it in data.weak_signals)
    draft = _one(generate_posts(data), SURFACE_X, PIECE_WEAK_SIGNAL)

    assert draft.source_urls == expected
    for url in expected:
        assert url in draft.text, "a source URL was lost from the X draft under truncation"
    # No URL survived only as a truncated stub — a cut URL is a dead URL, not a preserved one.
    for url in re.findall(r"https://\S*…", draft.text):
        pytest.fail(f"a URL was ellipsised: {url!r}")


def test_x_hook_keeps_a_readable_label_beside_a_long_url():
    """D-025: a 162-char source URL must starve the sentence, never the subject of the post."""
    draft = _one(generate_posts(long_form_digest()), SURFACE_X, PIECE_WEAK_SIGNAL)
    from tests.posts_fixtures import DRIVER

    assert len(draft.hook) <= X_CHAR_LIMIT
    assert DRIVER in draft.hook, f"the driving entity was trimmed out of the hook: {draft.hook!r}"
    # The link is still in the draft — displaced into the thread when it cannot share the hook.
    assert draft.source_urls[0] in draft.text


# ---- Defect 3: the Noise Report cap ----


def test_noise_report_respects_limit():
    """At most `NOISE_REPORT_LIMIT` items are NAMED, on all three surfaces, loudest first."""
    limit = settings.noise_report_limit
    bundle = generate_posts(noisy_digest(40))

    for surface in (SURFACE_X, SURFACE_LINKEDIN, SURFACE_MEDIUM):
        draft = _one(bundle, surface, PIECE_NOISE_REPORT)
        named = _fact_lines(draft)
        assert named, f"{surface} named no demoted items at all"
        assert len(named) <= limit, f"{surface} names {len(named)} items, over the {limit} cap"
        assert len(draft.source_urls) <= limit, f"{surface} carries {len(draft.source_urls)} URLs"

    # The cap is loudest-first: every named item is a hype-5 one, none of the hype-4 tail.
    medium = _one(bundle, SURFACE_MEDIUM, PIECE_NOISE_REPORT)
    assert "hype 5/5" in medium.text and "hype 4/5" not in medium.text
    # The 141 KB regression: the capped Medium draft is a readable document.
    assert len(medium.text) < 20_000, f"Medium noise report is {len(medium.text)} bytes"


def test_noise_report_states_true_total():
    """The cap must never misrepresent corpus size — the FULL demoted count is stated everywhere."""
    total = 40
    bundle = generate_posts(noisy_digest(total))
    shown = settings.noise_report_limit

    for surface, sentence in (
        (SURFACE_X, f"{total} items were demoted this week; these are the 5 loudest."),
        (SURFACE_LINKEDIN, f"{total} stories that were all volume, little signal. The 3 loudest:"),
        (SURFACE_MEDIUM, f"{total} items were demoted this week; these are the {shown} loudest."),
    ):
        text = _one(bundle, surface, PIECE_NOISE_REPORT).text
        assert sentence in text, f"{surface} never states the true demoted total ({total})"
        assert f"{shown} stories" not in text, f"{surface} presents the capped count as the total"

    # And on an uncapped week the wording stays honest — no phantom "here are the N loudest".
    small = _one(generate_posts(converging_digest()), SURFACE_MEDIUM, PIECE_NOISE_REPORT)
    assert "2 item(s) were demoted this week." in small.text
    assert "loudest." not in small.text
