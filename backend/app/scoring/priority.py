"""Canonical scoring scales and the single source of truth for priority classes.

This module is PURE LOGIC: no I/O, no config, no pipeline wiring. Task 005 (enrichment) imports
``compute_priority_class`` from here; nothing in this repo re-derives the rule inline.
"""

# Scoring polarity convention:
#   relevance, novelty, actionability, strategic_potential -> higher = MORE salient (0..5)
#   hype is INVERTED: 0 = strong signal, 5 = pure noise. Never sum hype additively with the
#   others; treat it as a penalty/demotion or filter.

# Each score is an integer on this inclusive range.
SCORE_MIN = 0
SCORE_MAX = 5

# The four "higher = more salient" axes.
SALIENT_SCORES = ("relevance", "novelty", "actionability", "strategic_potential")

# The inverted axis (0 = signal, 5 = noise). Kept separate on purpose.
INVERTED_SCORES = ("hype",)

PRIORITY_CLASSES = ("immediate_priority", "operational_update", "horizon_signal", "archive")


def compute_priority_class(relevance: int, strategic_potential: int) -> str:
    """Canonical priority-class rule.

    FIX vs the original brief: a relevance-5 item ("requires immediate attention") now floors
    to immediate_priority regardless of strategic_potential. The original rule demoted it to
    operational_update whenever strategic_potential < 3 — e.g. a security advisory in our own
    stack, maximally relevant but not 'strategic', was silently downgraded.
    """
    if relevance >= 5:
        return "immediate_priority"
    if relevance >= 4 and strategic_potential >= 3:
        return "immediate_priority"
    if relevance >= 3:
        return "operational_update"
    if strategic_potential >= 4:           # relevance <= 2 here by fall-through:
        return "horizon_signal"            # the low-relevance / high-future quadrant
    return "archive"
