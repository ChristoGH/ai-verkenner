"""Mention weight (task 016 / D-057) — is the driving entity *present* in an item, or merely named?

The convergence read counts **mentions**, and every extracted entity occurrence is worth the same.
So a piece whose headline is the driver and a retrospective that name-checks it once, at the end of
an 84-character blurb, contribute equally to a cluster and to the "N independent sources" claim
printed on the draft. That number is the load-bearing claim of the whole Weak Signal piece, and the
same defect has now been observed three times (the original 8-item "LLM" cluster, D-036, D-052) —
CLAUDE.md's "no abstraction before three real use cases" threshold.

This module answers one question about one **entity–item link**: how strongly is `driver` present in
*this* item's own text? It is deliberately the cheapest thing that works, in the preference order
task 016 sets out:

1. **mention count within the item** — one occurrence is a reference; two or more is a subject;
2. **title / lead presence versus body-only** — what a piece is *about* tends to reach its headline;
3. the enrichment `category` / `tags` — **evaluated and rejected**, see below.

There is **no LLM call, no embedding and no re-enrichment** here; it is string matching over text
the corpus already holds, so it costs nothing to run.

**Why the tags signal is not used.** Signal 3 is the documented fallback for when 1 and 2 do not
separate the cases. On the real corpus they do, and tags actively *mis*-classify: The Register's
NextBSD story (D-052) mentions Claude Code exactly once, in the last twelve characters of its feed
blurb, and the enrichment still tagged it `claude-code` — identically to the item whose headline is
`Claude Code uses Bun written in Rust now`. Tags record that an entity was *noticed*, which is the
very thing being measured, so they cannot also be the measure of it.

**This is not a topicality gate.** "Is this item about AI at all" is a different question, owned by
the source registry and the classifier, and explicitly out of scope (task 016 non-goals). A weight
here says only *how present the driver is* — an item can be strongly about Firefox and not about AI,
and this module will score it 1.0. That case is D-036, and it is a corpus-scope defect, not a
mention-weight one.

Nothing here is deleted, re-scored or removed from the graph: the weight feeds **cluster membership
only** (`digests.sections.coherent_cluster`). An item below the floor stays in the corpus, in the
graph, in the noise report and in every other digest section.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

# The bands, highest first. Named constants so tests and the audit log agree on what a number means
# and nobody re-derives "0.2 means passing" inline.
WEIGHT_TITLE = 1.0       # the driver is in the item's own headline — it is the subject
WEIGHT_REPEATED = 0.8    # named two or more times in the body — sustained, not a mention in passing
WEIGHT_LEAD = 0.6        # named in the opening of a body long enough to *have* an opening
WEIGHT_PASSING = 0.2     # named exactly once, body-only, past the lead — a reference
WEIGHT_ABSENT = 0.0      # never named in the item's own text

# How much of the body counts as its "lead". Applied ONLY when the body is longer than this: a feed
# blurb shorter than the lead window has no lead/body distinction to make, and treating one as all
# lead would score The Register's 84-character NextBSD teaser as a headline claim.
LEAD_CHARS = 200

_TAG_RE = re.compile(r"<[^>]+>")
_SEPARATORS = re.compile(r"[\s\-_]+")


@dataclass(frozen=True)
class MentionWeight:
    """One entity–item link's weight, with the reason it got it (the audit trail is the point)."""

    weight: float
    why: str
    count: int = 0          # occurrences across title + body
    in_title: bool = False

    @property
    def is_substantive(self) -> bool:
        """Convenience for readers; the actual membership floor is `CLUSTER_MEMBER_MIN_WEIGHT`."""
        return self.weight >= WEIGHT_LEAD


def plain_text(text: str | None) -> str:
    """Feed markup → comparable prose: tags dropped, entities unescaped, whitespace collapsed."""
    return " ".join(html.unescape(_TAG_RE.sub(" ", text or "")).split())


def _matcher(driver: str) -> re.Pattern[str] | None:
    """A whole-word, separator-tolerant pattern for `driver` ("Claude Code" ≡ "claude-code").

    Tolerant on separators because publishers, tags and prose disagree about them; strict on word
    boundaries because "AI" must not match "OpenAI" and "Claude" must not match "Claudette".
    """
    parts = [re.escape(p) for p in _SEPARATORS.split(driver.strip()) if p]
    if not parts:
        return None
    return re.compile(r"(?<!\w)" + r"[\s\-_]*".join(parts) + r"(?!\w)", re.IGNORECASE)


def mention_weight(
    driver: str, *, title: str, body: str, lead_chars: int = LEAD_CHARS
) -> MentionWeight:
    """How substantively `driver` is present in this one item. Pure, offline, free.

    `title` and `body` are the item's **own** text — the headline and the feed body it was published
    with (markup is stripped here, so raw feed HTML can be passed straight in).
    """
    pattern = _matcher(driver)
    if pattern is None:
        return MentionWeight(WEIGHT_ABSENT, "no driving entity", 0, False)

    title_text = plain_text(title)
    body_text = plain_text(body)
    title_hits = pattern.findall(title_text)
    body_hits = list(pattern.finditer(body_text))
    count = len(title_hits) + len(body_hits)

    if title_hits:
        return MentionWeight(WEIGHT_TITLE, "named in the title", count, True)
    if len(body_hits) >= 2:
        return MentionWeight(
            WEIGHT_REPEATED, f"named {len(body_hits)}x in the body", count, False
        )
    if not body_hits:
        return MentionWeight(WEIGHT_ABSENT, "never named in the item's own text", 0, False)

    start = body_hits[0].start()
    if len(body_text) > lead_chars and start < lead_chars:
        return MentionWeight(WEIGHT_LEAD, "named in the lead", count, False)
    return MentionWeight(
        WEIGHT_PASSING,
        f"named once, body-only (character {start} of {len(body_text)})",
        count,
        False,
    )
