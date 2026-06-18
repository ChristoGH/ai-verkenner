"""Regression tests for the canonical priority-class rule.

The headline case is the bug this rule fixes: relevance 5 must floor to immediate_priority even
when strategic_potential is 0.
"""

import pytest

from app.scoring.priority import PRIORITY_CLASSES, compute_priority_class


def test_regression_relevance5_strat0_is_immediate():
    # The bug case: a maximally relevant item with zero strategic potential
    # (e.g. a security advisory in our own stack) must NOT be demoted.
    assert compute_priority_class(5, 0) == "immediate_priority"


@pytest.mark.parametrize(
    "relevance, strategic_potential, expected",
    [
        (5, 0, "immediate_priority"),   # regression: relevance-5 floors to immediate
        (4, 3, "immediate_priority"),   # high relevance + enough strategic
        (4, 2, "operational_update"),   # high relevance but not strategic enough
        (3, 5, "operational_update"),   # mid relevance dominates regardless of strategic
        (2, 4, "horizon_signal"),       # low now, high future — the weak-signal quadrant
        (1, 1, "archive"),              # neither relevant nor strategic
    ],
)
def test_priority_class_cases(relevance, strategic_potential, expected):
    assert compute_priority_class(relevance, strategic_potential) == expected


def test_all_results_are_valid_classes():
    for r in range(0, 6):
        for s in range(0, 6):
            assert compute_priority_class(r, s) in PRIORITY_CLASSES
