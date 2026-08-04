"""Tests for the calibrated classifier prompt (Task 012).

Offline and deterministic: these read the template off disk and the fallback module's source.
They do not call an LLM — calibration itself is measured by
`scripts/measure_calibration.py` and recorded in `docs/m8-calibration-notes.md`, because LLM
output is not deterministic and must not be asserted in a unit test.
"""

from __future__ import annotations

import inspect
import re
from datetime import datetime, timezone

from app.enrichment import fallback as fallback_mod
from app.enrichment import prompts
from app.scoring.priority import INVERTED_SCORES, SALIENT_SCORES

# The one sentence that must exist, in substance, in BOTH the template and fallback.py.
# Task 012 scope point 5: narrow the tiebreaker to hype, and keep the two from drifting.
_MIRRORED_TIEBREAKER = "the only tiebreaker is on hype"
_MIRRORED_RATIONALE = "assume noise until shown otherwise"
# The pre-Task-012 wording: a blanket downward tiebreaker on relevance (D-018). Must be gone.
_REMOVED_WORDING = "lower end of relevance"


def _normalise(text: str) -> str:
    """Lowercase, drop markdown marks, fold en/em dashes to '-', collapse whitespace.

    Underscores are NOT stripped — they are part of the axis names (`strategic_potential`).
    """
    folded = text.lower().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", re.sub(r"[`*#>]", "", folded))


def test_classify_template_renders():
    """The template loads and the user block renders with every input the template names."""
    system = prompts.load_template(prompts.CLASSIFY)
    assert system.strip()

    user = prompts.render_item_inputs(
        title="Sub-billion-parameter models match frontier LLMs on relation extraction",
        source_name="arXiv cs.CL",
        source_url="https://arxiv.org/abs/0000.00000",
        published_at=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
        content="Benchmark tables; no code released.",
        user_context="Solo engineer; Qdrant + Neo4j graph pipelines; cloud LLM extraction.",
    )
    for field in ("title", "source_name", "source_url", "published_at", "content", "user_context"):
        assert f"{field}:" in user

    # Every input the template claims the caller provides must actually be rendered.
    normalised_system = _normalise(system)
    claimed = re.findall(r"`([a-z_]+)`", system.split("## Task")[0])
    for name in {c for c in claimed if c in {"title", "source_name", "source_url",
                                             "published_at", "content", "user_context",
                                             "source_type"}}:
        assert f"{name}:" in user, f"template claims `{name}` is provided but it is not rendered"

    # All five axes are named, and none were added or renamed.
    for axis in (*SALIENT_SCORES, *INVERTED_SCORES):
        assert axis in system


def test_template_anchors_every_axis_including_top_of_scale():
    """Each axis carries 0-5 anchors — a 4 and a 5 must be defined, not left implicit (D-018)."""
    system = prompts.load_template(prompts.CLASSIFY)
    sections = system.split("### ")
    for axis in (*SALIENT_SCORES, *INVERTED_SCORES):
        block = next((s for s in sections if s.startswith(f"`{axis}`")), None)
        assert block is not None, f"no anchor block for `{axis}`"
        for value in range(6):
            assert f"- `{value}` —" in block, f"`{axis}` is missing an anchor for {value}"


def test_template_states_the_decoupling_rule():
    """strategic_potential is scored first and independently; the low-rel/high-strat combination
    is stated as valid. This is the fix D-018 asked for; losing it re-creates the collinearity."""
    system = _normalise(prompts.load_template(prompts.CLASSIFY))
    assert "strategic_potential first" in system
    assert "independently" in system
    assert "relevance 0-1 and strategic_potential 4-5" in system
    # The worked example of the low-relevance / high-strategic quadrant.
    assert "worked example" in system
    assert "low-relevance / high-strategic" in system


def test_strategic_potential_is_framed_on_the_problem_space_not_the_stack():
    """Scope point 6 (D-049): `strategic_potential`'s anchors key on the shape of the problem, not
    on nearness to the current stack. Attempt 1 measured r = 0.749 precisely because both axes were
    anchored to `user_context`; re-anchoring them there again re-creates the collinearity."""
    system = prompts.load_template(prompts.CLASSIFY)
    block = next(s for s in system.split("### ") if s.startswith("`strategic_potential`"))
    normalised = _normalise(block)

    # The problem space is named, so the axis has evidence of its own to score against.
    for phrase in ("agentic pipelines", "retrieval and knowledge graphs",
                   "evaluation and traceability", "trust-sensitive domains"):
        assert phrase in normalised, f"the problem space no longer names {phrase!r}"
    assert "shape of the problem" in normalised

    # The attempt-1 anchors that made the axis a restatement of `relevance` must not come back.
    for banned in ("already in the stack", "an area they build in"):
        assert banned not in normalised, f"strategic_potential is anchored on the stack again: {banned!r}"

    # And the axis must say plainly that stack-distance is not evidence against it.
    assert "touches nothing the user runs today can still score" in normalised


def test_fallback_wording_matches_template():
    """Pin the mirror: the hype-only tiebreaker is stated in both, and the old blanket
    downward tiebreaker on relevance is stated in neither."""
    template = _normalise(prompts.load_template(prompts.CLASSIFY))
    source = _normalise(inspect.getsource(fallback_mod))

    for phrase in (_MIRRORED_TIEBREAKER, _MIRRORED_RATIONALE):
        assert phrase in template, f"template lost the mirrored wording: {phrase!r}"
        assert phrase in source, f"fallback.py lost the mirrored wording: {phrase!r}"

    assert _REMOVED_WORDING not in template
    assert _REMOVED_WORDING not in source


def test_hype_inversion_still_stated():
    """The inversion is a standing invariant (CLAUDE.md); calibration must not have touched it."""
    system = _normalise(prompts.load_template(prompts.CLASSIFY))
    assert "hype is inverted" in system
    assert "0 = strong signal" in system
    assert "5 = pure noise" in system
