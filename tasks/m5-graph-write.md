# Task M5 — Graph write + graph-aware ranking

**Status: DONE** ✅ (commit `9d09209`, branch `feat/m5-graph-write`)

> Traceability stub. M5 was built ahead of a dedicated task file. Full specification:
> [`../docs/PHASE_1_PLAN.md`](../docs/PHASE_1_PLAN.md) §3 (graph schema) + §5 (M5);
> [`../docs/decisions/0001-graph-vector-visual-stack.md`](../docs/decisions/0001-graph-vector-visual-stack.md).

## Goal

Project the SQLite entities/relationships/items/events/topics into a Neo4j knowledge graph, and add
a graph-aware ranking signal (convergence + centrality + recency) layered **on top of** the
canonical priority class — never changing the class, always keeping hype a demotion.

## Scope (as built)

- `app/graph/`: `GraphStore` protocol; `neo4j_store` (idempotent MERGE, label/edge whitelists,
  convergence query); in-memory store (test double mirroring MERGE semantics); `projection`
  (`project_new_events` degrade-don't-crash, `graph_reindex`); `util` (schema constants,
  entity-type→label, UTC normalisation). Schema: Item/Source/Entity(:Org/:Model/:Person/:Tool/
  :Concept)/Event/Topic + FROM, IN_EVENT, MENTIONS{ts}, INTERACTS_WITH{ts,kind}, ABOUT.
- `app/scoring/graph_signals.py`: convergence (distinct sources in window) + degree + recency →
  weighted score with a human-readable `why`.
- `app/scoring/ranking.py`: `rank_with_graph` blends the graph score into the **within-class
  tiebreak only** — priority class is the primary sort key (untouched); hype still subtracted.
- `EnrichedItem.projected` flag; pipeline projects new enriched Events; `cli run --no-graph` +
  `graph-reindex`; `GRAPH_*` weights + window in config.

## Non-goals

No `/graph` endpoint or Cosmograph (M6), no MCP, no fuzzy entity resolution, no LLM changes.

## Acceptance criteria (met)

- Idempotent MERGE projection (re-run adds no duplicate nodes/edges).
- `graph_reindex` rebuilds Neo4j purely from SQLite; counts match a live projection.
- A simulated Neo4j write failure leaves the Event `projected=False`, SQLite intact, run does not
  raise.
- Convergence promotes an item **within** its class without changing the class; hype still demotes.
- Existing tests pass; unit suite needs no live Neo4j.

## Known follow-ups (Phase 2)

Convergence **trajectory** (growth-rate, not snapshot) and **source-independence weighting**; the
weak-signal **selection** query (filter to the horizon/archive quadrant, rank by graph score) is an
M7/M7.5 deliverable — see [`../docs/PHASE_1_PLAN.md`](../docs/PHASE_1_PLAN.md) §7.

## Constraints

One slice; human review gate before merge; SQLite is the source of truth, Neo4j a rebuildable
derived index.
