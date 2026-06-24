"""API response shapes (M6) — what the dashboard reads.

These are the *output* contracts for `/items`, `/graph`, and `/horizon`. They keep the core
invariants visible at the surface: every item carries its **source_url**, the **five scores** with
hype labelled inverted, **summary (fact)** kept separate from **why_it_matters / recommended_action
(interpretation)**, the **priority_class** (from the canonical rule), and the graph signal's `why`.
"""

from __future__ import annotations

from pydantic import BaseModel


class ScoresOut(BaseModel):
    """The five scores. hype is INVERTED: 0 = strong signal, 5 = pure noise."""

    relevance: int
    novelty: int
    actionability: int
    strategic_potential: int
    hype: int


class ItemOut(BaseModel):
    """One ranked enriched item (Core Radar)."""

    id: str
    title: str
    source_name: str
    source_url: str            # always preserved
    published_at: str | None
    priority_class: str
    category: str
    tags: list[str]
    scores: ScoresOut
    summary: str               # SOURCE FACT
    why_it_matters: str        # INTERPRETATION
    recommended_action: str    # INTERPRETATION
    is_weak_signal: bool
    horizon: str | None
    graph_why: str             # which graph signal fired (may be empty)
    convergence: int           # distinct sources on the driving entity (0 if none)


class HorizonItemOut(ItemOut):
    """A weak-signal item ranked by graph convergence, with its evidence."""

    graph_score: float
    contributing_sources: list[str]


class GraphNodeOut(BaseModel):
    id: str
    label: str
    kind: str                  # "entity" | "event"
    type: str | None = None
    priority_class: str | None = None
    ts: str | None = None


class GraphLinkOut(BaseModel):
    source: str
    target: str
    kind: str                  # "interacts" | "mentions"
    ts: str | None = None


class GraphOut(BaseModel):
    nodes: list[GraphNodeOut]
    links: list[GraphLinkOut]
    truncated: bool = False
    available: bool = True      # False when Neo4j is unreachable (degraded, empty graph)


class HorizonOut(BaseModel):
    items: list[HorizonItemOut]
    graph_available: bool = True


class FeedbackIn(BaseModel):
    """The body of POST /items/{id}/feedback — the action the user took (M7)."""

    action: str  # useful | not_useful | save | ignore (validated against scoring.feedback)


class FeedbackOut(BaseModel):
    """The persisted feedback record (M7)."""

    id: int
    event_id: int
    action: str
    created_at: str


class DigestSummaryOut(BaseModel):
    """One row in GET /digests — enough to list and pick a digest (M7)."""

    id: int
    period_start: str | None
    period_end: str | None
    generated_at: str
    method: str            # "llm" | "fallback"
    item_count: int        # Events considered for the body
    noise_count: int       # archived / high-hype Events excluded (honest count)
    graphrag: bool         # whether Qdrant-retrieve / Neo4j-expand actually ran


class DigestOut(DigestSummaryOut):
    """A full digest from GET /digests/{id} — the rendered briefing plus referenced events."""

    content_md: str
    event_ids: list[int]
