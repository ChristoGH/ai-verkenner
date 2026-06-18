"""Scoring: pure logic for scores and the canonical priority rule.

Import the priority rule from here; do not re-derive it elsewhere.
"""

from app.scoring.priority import (
    PRIORITY_CLASSES,
    SALIENT_SCORES,
    INVERTED_SCORES,
    SCORE_MAX,
    SCORE_MIN,
    compute_priority_class,
)

__all__ = [
    "compute_priority_class",
    "PRIORITY_CLASSES",
    "SALIENT_SCORES",
    "INVERTED_SCORES",
    "SCORE_MIN",
    "SCORE_MAX",
]
