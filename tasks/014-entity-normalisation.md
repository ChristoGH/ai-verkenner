# Task 014 — Entity normalisation: one concept, one uid

**Status: IMPLEMENTED — AT THE REVIEW GATE (2026-08-04).** Precondition verified in code, not
docs: Task 013 is merged at `1873d78` (quietness selection + `WEAK_DRIVER_STOPLIST` + the defect-C
floors are all present in HEAD). Raised by [D-024](../docs/DECISIONS.md), sequenced by
[D-026](../docs/DECISIONS.md); decisions D-058…D-061 recorded.

**Measured on 2026-07-14 → 07-21** (before = graph as built with resolution disabled, after =
`graph-reindex` with the map on): distinct entities **793 → 788**, distinct drivers **30 → 26**,
largest group **12 → 27**, weak-signal driver **`Claude Code` (3 items) → unchanged**.

**The sequencing was load-bearing.** The AI/LLM family — **six** rows, not the five D-024 recorded —
merges from a largest fragment of 7 items into a single **27-item** group, by far the largest in the
quadrant. Under the old "largest group wins" rule this task would have produced the worst possible
weak signal; with 013 in place the merged node is stoplisted and selection does not move.
See [D-061](../docs/DECISIONS.md) for the caveat that no *vendor* family is fragmented in this
corpus, so the false-negative fix is demonstrated but not yet load-bearing on real output.

## ⚠️ Read this before starting

**Normalisation on its own makes the weak-signal defect worse.** Merging "AI", "LLM", "LLMs",
"Large language models" and "Artificial Intelligence" into a single uid creates one *larger* hub. If
Task 013's concept-node stoplist and quietness-based selection are not already in place, that merged
hub becomes an even more dominant "largest group" and is more likely to be surfaced as the weak
signal, not less.

**Task 013 must be merged before this task starts.** If it is not, stop and say so.

## Goal

One concept has one entity uid across the graph, so driver counts are honest and genuine clusters
stop fragmenting.

## Context

D-024 measured the 2026-07-14 → 07-21 horizon quadrant: 84 items with `convergence > 0` resolving to
**30 distinct drivers** — but among those drivers, **"AI", "LLM", "LLMs", "Large language models"
and "Artificial Intelligence" are five separate uids for one concept**, carrying 6, 5, ?, 7 and ?
items respectively.

Two harms, in opposite directions:

1. **Inflated driver counts.** 30 "distinct" drivers overstates the diversity of the corpus, and
   makes convergence look broader than it is.
2. **Fragmented real clusters.** Items that genuinely converge on one entity are split across alias
   uids, so a real signal can fall below `WEAK_CLUSTER_MIN_ITEMS` and be missed entirely. This one is
   the more damaging for an early-warning product — it is a *false negative* generator.

## Scope

- An explicit **alias map** applied at graph projection time, mapping surface forms to a canonical
  entity identity. At minimum: case folding, singular/plural collapse, and a curated synonym list
  covering the LLM/AI concept family and common vendor spellings (e.g. `OpenAI` / `Open AI`,
  `DeepMind` / `Google DeepMind`).
- The map lives in a **human-editable file** (YAML alongside `sources.yaml`, or config), not inline
  in code. Every entry is auditable; a human can see exactly what was merged into what.
- Applied on projection, so `graph-reindex` fully rebuilds the normalised graph from SQLite. **No
  destructive migration** — SQLite is the source of truth and Neo4j is a rebuildable derived index
  (ADR 0001).
- Record before/after counts: total distinct entities, distinct drivers in the horizon quadrant, and
  the size of the largest group.

## Non-goals

- **No fuzzy matching, no embedding-based entity resolution, no ML entity typing.** An explicit,
  reviewable alias map only. Automatic entity resolution is a large project and is not sanctioned by
  any task file.
- No change to entity *extraction* in enrichment — this normalises what is already extracted.
- No change to convergence maths, `GRAPH_MIN_SOURCES`, or `priority.py`.
- Do not remove Task 013's stoplist. Normalisation and exclusion are complementary: the stoplist
  must still catch the *merged* concept node. Verify it does.

## Acceptance criteria

- The five AI/LLM concept uids collapse to one canonical identity, and Task 013's stoplist still
  makes that canonical identity ineligible as a driver. **Assert this explicitly** — it is the whole
  reason for the sequencing.
- `graph-reindex` reproduces the normalised graph from SQLite alone, repeatably.
- Before/after report: distinct entities, distinct drivers, largest group size, and whether the
  weak-signal driver selected by Task 013 changes as a result.
- At least one previously-fragmented cluster is shown to merge — i.e. demonstrate the false-negative
  fix, not just the count reduction.
- Full backend suite green. Re-verify the baseline; do not trust the recorded number (D-022).

## Test plan

- `test_alias_map_collapses_concept_family` — the five AI/LLM forms resolve to one uid.
- `test_canonical_concept_still_stoplisted` — pins the 013 interaction; the merged node cannot become
  a driver.
- `test_normalisation_is_idempotent` — reindexing twice yields identical entity identities.
- `test_unmapped_entities_pass_through_unchanged` — nothing outside the map is altered.
- `test_reindex_rebuilds_from_sqlite_alone` — no dependence on prior graph state.

## Files likely to change

`backend/app/graph/projection.py` · `backend/app/graph/util.py` · a new alias file
(`sources/entity_aliases.yaml` or equivalent) · `backend/app/core/config.py` · `backend/tests/`

---

## Agent prompt (paste-ready)

```
Read HANDOFF.md, then CLAUDE.md, then docs/AGENT_ADDENDUM.md, then docs/DECISIONS.md
entries D-024 and D-026, then tasks/014-entity-normalisation.md. All binding.

FIRST — VERIFY THE PRECONDITION. Task 013 (driver eligibility: quietness-based
selection + WEAK_DRIVER_STOPLIST) MUST already be merged. Check the code, not the
docs. If it is not present, STOP and report — do not proceed. Normalisation without
013 merges the AI/LLM aliases into one LARGER hub and makes the weak-signal defect
worse, which is the entire reason for this ordering.

GOAL: one concept, one entity uid.

CONTEXT: D-024 measured 30 distinct drivers in the 2026-07-14 -> 07-21 horizon
quadrant, but "AI", "LLM", "LLMs", "Large language models" and "Artificial
Intelligence" are FIVE separate uids for one concept. This inflates driver counts and —
more damagingly — fragments genuine clusters below WEAK_CLUSTER_MIN_ITEMS, so real
signals are missed. That is a false-negative generator in an early-warning product.

SCOPE: an explicit, human-editable alias map applied at GRAPH PROJECTION time. Case
folding, singular/plural collapse, and a curated synonym list for the AI/LLM concept
family plus common vendor spellings (OpenAI/Open AI, DeepMind/Google DeepMind). Keep it
in YAML next to sources.yaml — every merge must be auditable by a human reading one
file.

HARD CONSTRAINTS
- NO fuzzy matching, NO embeddings, NO ML entity typing. Explicit map only.
- No change to entity EXTRACTION in enrichment — normalise what is already extracted.
- No change to convergence maths, GRAPH_MIN_SOURCES, or priority.py (D-014).
- Do NOT remove or weaken task 013's stoplist. Verify it still catches the MERGED
  canonical node — assert it in a test.
- Rebuild only via graph-reindex from SQLite (ADR 0001). No destructive migration.

TESTS: the five named in the task file.

ACCEPTANCE
- Five concept uids collapse to one; the canonical node is still stoplisted.
- Before/after report: distinct entities, distinct drivers, largest group size, and
  whether task 013's selected weak-signal driver changes.
- Demonstrate at least one previously-fragmented cluster MERGING — the false-negative
  fix, not just a smaller count.
- Full suite green. RE-VERIFY the baseline count; do not trust the recorded number
  (D-022, date-dependent fixtures).
- CHANGELOG.md entry; D-NNN entries for unasked choices; overwrite HANDOFF.md.

STOP CONDITIONS
- Task 013 not merged -> STOP (see above).
- If normalisation would require changing entity extraction or adding a resolution
  model to work, STOP and report. That is a different, unsanctioned project.
```
