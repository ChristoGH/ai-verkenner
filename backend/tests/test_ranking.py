"""Tests for the hype-aware ranking helper (M4).

The headline guarantee: hype is a demotion, never summed with the other axes — a high-hype item
ranks below an otherwise-identical low-hype one.
"""

from dataclasses import dataclass

from app.scoring.ranking import rank, salience


@dataclass
class _Item:
    relevance: int
    novelty: int
    actionability: int
    strategic_potential: int
    hype: int
    priority_class: str = "operational_update"


def test_salience_subtracts_hype_never_adds():
    low = _Item(4, 4, 4, 4, hype=0)
    high = _Item(4, 4, 4, 4, hype=5)
    # Same salient axes; salience must DROP as hype rises (penalty, not bonus).
    assert salience(low) == 16          # 4+4+4+4 - 0
    assert salience(high) == 11         # 4+4+4+4 - 5
    assert salience(high) < salience(low)


def test_high_hype_high_relevance_ranks_below_low_hype_equivalent():
    loud = _Item(5, 4, 4, 4, hype=5)   # high relevance but pure noise
    quiet = _Item(5, 4, 4, 4, hype=0)  # identical, but low hype
    ordered = rank([loud, quiet])
    assert ordered[0] is quiet
    assert ordered[1] is loud


def test_priority_class_dominates_then_salience():
    immediate_noisy = _Item(5, 0, 0, 0, hype=5, priority_class="immediate_priority")
    archive_clean = _Item(5, 5, 5, 5, hype=0, priority_class="archive")
    # Priority class wins even though the archive item has higher raw salience.
    ordered = rank([archive_clean, immediate_noisy])
    assert ordered[0] is immediate_noisy
    assert ordered[1] is archive_clean


def test_rank_orders_by_salience_within_a_class():
    a = _Item(2, 2, 2, 2, hype=0, priority_class="operational_update")  # salience 8
    b = _Item(4, 4, 2, 2, hype=0, priority_class="operational_update")  # salience 12
    ordered = rank([a, b])
    assert ordered == [b, a]
