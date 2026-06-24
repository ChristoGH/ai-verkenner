"""Feedback → ranking adjustment (M7) — transparent, documented, and class-preserving.

A user's feedback (useful / not_useful / save / ignore) folds into ranking the **same disciplined
way** the M5 graph signal does: as an additive term in the *within-class* tiebreak only. It never
changes the canonical priority class (`compute_priority_class` stays the one source of truth) and it
never overrides the hype inversion — the adjustment is added to `scoring/ranking.salience`, which
already subtracts hype, so a noisy item a user marked "useful" still ranks below its low-hype twin.

The rule (deliberately simple and explainable):

- **useful / save** → a positive lift.
- **not_useful** → a demotion.
- **ignore** → removed from the default feed entirely (and, if ever shown, a demotion).

Feedback rows are append-only history. The **latest** action per Event wins, so a user can change
their mind (mark useful, later ignore) and the most recent decision is the one that counts.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Feedback

# The four actions the UI offers. Kept here so the API validates against one list.
FEEDBACK_ACTIONS = ("useful", "not_useful", "save", "ignore")

# Per-action weight, scaled by `settings.feedback_weight` when it blends into the tiebreak.
# useful/save lift; not_useful/ignore demote. (`ignore` also removes from the default feed.)
FEEDBACK_WEIGHTS: dict[str, float] = {
    "useful": 1.0,
    "save": 1.0,
    "not_useful": -1.0,
    "ignore": -1.0,
}

# The action that hides an Event from the default feed.
HIDE_ACTION = "ignore"


@dataclass(frozen=True)
class FeedbackState:
    """The net, latest-wins feedback state for one Event."""

    action: str          # the latest action recorded
    weight: float        # FEEDBACK_WEIGHTS[action] (the unscaled tiebreak delta)
    hidden: bool         # True when the latest action is `ignore` (drop from the default feed)


def latest_feedback(rows: list[Feedback]) -> dict[int, FeedbackState]:
    """Collapse append-only feedback history to the latest action per Event.

    "Latest" = newest `created_at`, breaking ties by `id` (insertion order) so the result is
    deterministic even when several actions share a timestamp (as in tests).
    """
    latest: dict[int, Feedback] = {}
    for row in rows:
        prev = latest.get(row.event_id)
        if prev is None or _is_newer(row, prev):
            latest[row.event_id] = row

    out: dict[int, FeedbackState] = {}
    for event_id, row in latest.items():
        action = row.action
        weight = FEEDBACK_WEIGHTS.get(action, 0.0)
        out[event_id] = FeedbackState(action=action, weight=weight, hidden=action == HIDE_ACTION)
    return out


def _is_newer(candidate: Feedback, current: Feedback) -> bool:
    c_ts, cur_ts = candidate.created_at, current.created_at
    if c_ts != cur_ts:
        return c_ts > cur_ts
    return (candidate.id or 0) > (current.id or 0)


def feedback_deltas(states: dict[int, FeedbackState]) -> dict[int, float]:
    """The per-Event unscaled tiebreak delta (the ranking layer scales by `feedback_weight`)."""
    return {event_id: st.weight for event_id, st in states.items()}


def hidden_event_ids(states: dict[int, FeedbackState]) -> set[int]:
    """Events whose latest action is `ignore` — removed from the default feed."""
    return {event_id for event_id, st in states.items() if st.hidden}
