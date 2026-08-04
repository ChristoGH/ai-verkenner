"""Rule-based enrichment fallback (M4).

Borrowed from the news-aggregator pattern: when the LLM is unavailable or its output can't be
parsed, degrade gracefully to a deterministic minimal enrichment rather than aborting the run
(fail-safe per item). It still produces a valid `EnrichedItem` — the five scores (hype inverted),
a fact-only summary, and clearly-marked interpretation placeholders — so the pipeline never stalls
on a bad/missing LLM call. No entities/relationships are guessed here (precision over recall).

This intentionally does **not** import or re-derive the priority rule; the enricher computes the
priority class from these scores via `app/scoring/priority.compute_priority_class`.
"""

from __future__ import annotations

from app.models import RawItem
from app.schemas.enrichment import (
    ClassifyResult,
    GraphExtractResult,
    Scores,
    SummariseResult,
    WeakSignalResult,
)

# A small, fixed stack/interest vocabulary. Conservative on purpose: keyword overlap is a weak
# proxy for relevance, so this path caps it low. Mirrors prompts/classify_item.md (Task 012) —
# the only tiebreaker is on hype: when unsure how promotional an item is, prefer the higher end
# of hype (assume noise until shown otherwise). No such downward tiebreaker applies to relevance,
# strategic_potential, novelty, or actionability.
#
# These keywords score RELEVANCE ONLY. `strategic_potential` is scored against the shape of the
# problem space — agentic pipelines, retrieval and knowledge graphs, evaluation and traceability,
# trust-sensitive domains — and NOT against the contents of the current stack (Task 012 scope
# point 6, D-049). Keyword overlap with the stack is therefore evidence for relevance and evidence
# for nothing else; this path cannot judge the problem space, so it emits a flat, neutral 2 rather
# than deriving strategic_potential from the same keyword hits (which is precisely the collinearity
# the LLM prompt was rewritten to remove).
_STACK_KEYWORDS = (
    "python", "fastapi", "sqlite", "qdrant", "neo4j", "react", "typescript",
    "llm", "rag", "vector", "graph", "embedding", "agent", "anthropic", "claude",
    "openai", "transformer", "retrieval",
)
_ACTION_KEYWORDS = ("release", "released", "breaking", "deprecat", "security", "advisory", "cve")
_SUBSTANTIVE_TYPES = {"github_releases", "arxiv"}


def _clamp(value: int) -> int:
    return max(0, min(5, value))


def _text_of(item: RawItem) -> str:
    return f"{item.title} {item.summary or ''}".lower()


def fallback_enrichment(
    item: RawItem,
) -> tuple[ClassifyResult, SummariseResult, WeakSignalResult, GraphExtractResult]:
    """Produce a deterministic, conservative enrichment for one representative item."""
    text = _text_of(item)
    matched = [kw for kw in _STACK_KEYWORDS if kw in text]

    # Relevance from how much of the user's stack/interests the item touches (0..5, capped low).
    relevance = _clamp(min(len(matched), 4))
    actionable = any(kw in text for kw in _ACTION_KEYWORDS)
    substantive = item.source_type in _SUBSTANTIVE_TYPES

    scores = Scores(
        relevance=relevance,
        novelty=2,
        actionability=_clamp(2 if actionable else 1),
        # Neutral by construction — see the note above: this path has no way to judge the problem
        # space, and must not infer it from stack keywords.
        strategic_potential=2,
        # hype is INVERTED: lower = stronger signal. Trust substantive source types more.
        hype=_clamp(2 if substantive else 3),
    )

    if "security" in text or "advisory" in text or "cve" in text:
        category = "security"
    elif item.source_type == "github_releases":
        category = "tool_update"
    elif item.source_type == "arxiv":
        category = "research"
    else:
        category = "uncategorised"

    classify = ClassifyResult(category=category, tags=matched, scores=scores)

    summarise = SummariseResult(
        # Fact only: echo the source's own summary/title — never an inference.
        summary=(item.summary or item.title).strip(),
        why_it_matters="No LLM interpretation available (rule-based fallback).",
        connection_to_user_work=(
            "Mentions the user's stack/interests." if matched else "No direct connection detected."
        ),
        recommended_action="No action — awareness only (rule-based fallback).",
    )

    # The fallback never claims a weak signal — judging that needs the model.
    weak_signal = WeakSignalResult(is_weak_signal=False, rationale="rule-based fallback")
    graph = GraphExtractResult(entities=[], relationships=[])
    return classify, summarise, weak_signal, graph
