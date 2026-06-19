"""Ranking that respects the hype inversion (M4).

The four salient axes (relevance, novelty, actionability, strategic_potential) run higher = more
salient. **hype is inverted and is a demotion only** — it is subtracted as a penalty, never summed
in with the others. This module imports the axis names from `app/scoring/priority.py` (the single
source of truth) and does not re-derive the priority rule.

At M4 ranking is just priority class + hype-aware salience; graph-aware ranking is M5.
"""

from __future__ import annotations

from app.scoring.priority import PRIORITY_CLASSES, SALIENT_SCORES

# Lower index = higher priority. Derived from the canonical class tuple, not re-listed by hand.
_PRIORITY_ORDER = {cls: i for i, cls in enumerate(PRIORITY_CLASSES)}


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
    order = _PRIORITY_ORDER.get(getattr(item, "priority_class", None), len(_PRIORITY_ORDER))
    return (order, -salience(item))


def rank(items: list) -> list:
    """Return items ordered by priority class, then by hype-demoted salience (best first)."""
    return sorted(items, key=rank_key)
