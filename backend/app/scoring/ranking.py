"""Ranking that respects the hype inversion (M4) + graph-aware blend (M5).

The four salient axes (relevance, novelty, actionability, strategic_potential) run higher = more
salient. **hype is inverted and is a demotion only** — it is subtracted as a penalty, never summed
in with the others. This module imports the axis names from `app/scoring/priority.py` (the single
source of truth) and does not re-derive the priority rule.

Order is always **priority class first** (the canonical class, never changed here), then a tiebreak.
At M4 the tiebreak is hype-aware salience; at M5 `rank_with_graph` adds a graph signal on top of
that salience (still within the class, still hype-demoted).
"""

from __future__ import annotations

from collections.abc import Mapping

from app.core.config import settings
from app.scoring.priority import PRIORITY_CLASSES, SALIENT_SCORES

# Lower index = higher priority. Derived from the canonical class tuple, not re-listed by hand.
_PRIORITY_ORDER = {cls: i for i, cls in enumerate(PRIORITY_CLASSES)}


def _priority_order(item: object) -> int:
    return _PRIORITY_ORDER.get(getattr(item, "priority_class", None), len(_PRIORITY_ORDER))


def salience(item: object) -> float:
    """Salient-axis sum **minus** the hype penalty. Higher = should surface first.

    `item` is anything carrying the five score attributes (e.g. an `EnrichedItem`). hype is treated
    as a demotion: two otherwise-identical items rank the higher-hype one lower, and hype is never
    added to the salient axes.
    """
    base = sum(int(getattr(item, axis)) for axis in SALIENT_SCORES)
    return base - int(getattr(item, "hype"))


def rank_key(item: object) -> tuple[int, float]:
    """Sort key: priority class first, then descending hype-aware salience."""
    return (_priority_order(item), -salience(item))


def rank(items: list) -> list:
    """Return items ordered by priority class, then by hype-demoted salience (best first)."""
    return sorted(items, key=rank_key)


def _graph_score(item: object, signals: Mapping) -> float:
    """The graph adjustment for `item`, looked up by its `event_id` (0.0 if none)."""
    signal = signals.get(getattr(item, "event_id", None))
    return float(getattr(signal, "score", 0.0)) if signal is not None else 0.0


def _feedback_score(item: object, feedback: Mapping | None) -> float:
    """The feedback adjustment for `item`, looked up by its `event_id` (0.0 if none) (M7)."""
    if not feedback:
        return 0.0
    return float(feedback.get(getattr(item, "event_id", None), 0.0))


def graph_aware_key(
    item: object,
    signals: Mapping,
    *,
    signal_weight: float,
    feedback: Mapping | None = None,
    feedback_weight: float = 0.0,
) -> tuple[int, float]:
    """Sort key: priority class first, then (hype-aware salience + graph signal + feedback) (M5/M7).

    The graph signal AND the feedback adjustment only blend into the within-class tiebreak — neither
    moves an item between priority classes, and both are *added* to salience (which already subtracts
    hype), so a high-hype item with the same adjustments still ranks below its low-hype twin.
    """
    blended = (
        salience(item)
        + signal_weight * _graph_score(item, signals)
        + feedback_weight * _feedback_score(item, feedback)
    )
    return (_priority_order(item), -blended)


def rank_with_graph(
    items: list,
    signals: Mapping,
    *,
    signal_weight: float | None = None,
    feedback: Mapping | None = None,
    feedback_weight: float | None = None,
) -> list:
    """Rank by priority class, then hype-aware salience blended with graph + feedback signals (M5/M7).

    `signals` maps `event_id -> GraphSignal`; `feedback` (optional, M7) maps `event_id -> delta`
    (useful/save lift, not_useful demote). The priority class is untouched; hype still demotes. When
    `feedback` is omitted the result is identical to the M5 graph-only ranking.
    """
    weight = settings.graph_signal_weight if signal_weight is None else signal_weight
    fb_weight = settings.feedback_weight if feedback_weight is None else feedback_weight
    return sorted(
        items,
        key=lambda it: graph_aware_key(
            it, signals, signal_weight=weight, feedback=feedback, feedback_weight=fb_weight
        ),
    )
