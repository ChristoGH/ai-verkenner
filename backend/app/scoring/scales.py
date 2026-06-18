"""Scoring scale constants.

Re-exported from app.scoring.priority so callers have one obvious place to read the score
range and axis polarity. Keep this aligned with the canonical scoring section in the brief.
"""

from app.scoring.priority import (
    INVERTED_SCORES,
    SALIENT_SCORES,
    SCORE_MAX,
    SCORE_MIN,
)

# All five score axes, for validation/iteration.
ALL_SCORES = SALIENT_SCORES + INVERTED_SCORES

__all__ = ["ALL_SCORES", "SALIENT_SCORES", "INVERTED_SCORES", "SCORE_MIN", "SCORE_MAX"]
