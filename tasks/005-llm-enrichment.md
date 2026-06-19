# Task 005 (M4 — Enrichment + entity/relationship extraction) — LLM Enrichment

**Status: M4 — TODO**

## Goal

Enrich each new `RawItem` into an `EnrichedItem`: classification/tags, the five scores, summary,
why-it-matters, connection-to-user-work, and a recommended action — and derive the priority
class **by importing the canonical rule**, never re-implementing it.

## Scope

- An enrichment module that, for each new `RawItem`, calls the LLM using the templates in
  `prompts/` (`classify_item.md`, `summarise_item.md`, `weak_signal.md`) and produces an
  `EnrichedItem`.
- The five scores: `relevance`, `novelty`, `actionability`, `strategic_potential`, `hype`.
- Priority class computed via `app/scoring/priority.py` (`compute_priority_class`).
- Ranking that respects the **hype inversion** (hype is a demotion/filter, never additive).
- Persist `EnrichedItem` (extending the Task 004 storage).

## Non-goals

- No dashboard work (Task 006).
- No feedback loop (Task 007).
- No new scoring rule — use the one in `scoring/priority.py`.

## Hard requirement — single source of truth for the priority rule

Enrichment **must import** `app/scoring/priority.py` and call `compute_priority_class(...)`. It
must **not** re-implement, copy, or inline the priority logic anywhere. It must respect the hype
inversion when ranking: a high-`hype` item is demoted or filtered, never lifted, and `hype` is
never summed additively with the other four scores.

## Scoring section (canonical — verbatim; keep in sync with the brief and `priority.py`)

<!-- BEGIN CANONICAL SCORING SECTION (verbatim — keep in sync with priority.py and the brief) -->

### Scores (each 0–5 integer)

- **relevance** — how directly this affects the user's current work and stack.
  Higher = more relevant. `5` means "requires immediate attention".
- **novelty** — how new or surprising this is versus what is already known.
  Higher = more novel.
- **actionability** — how clearly this implies a concrete action the user could take.
  Higher = more actionable.
- **strategic_potential** — how much this could matter to the user's future direction,
  independent of today's relevance. Higher = more strategic.
- **hype** — how much this is noise / marketing / overstatement rather than substance.
  **INVERTED polarity: `0` = strong signal, `5` = pure noise.**

### Polarity rule (do not get this wrong)

`relevance`, `novelty`, `actionability`, and `strategic_potential` all run **higher = more
salient**. `hype` is **inverted**. Never sum `hype` additively with the other four. Treat it as a
**penalty / demotion** (or a filter): a high-hype item is pushed down or out, never lifted.

### Priority classes

Items are bucketed into one of four priority classes, computed **only** by the canonical rule in
`backend/app/scoring/priority.py` (`compute_priority_class`). Do not re-derive this inline
anywhere else — import it.

- **immediate_priority** — needs attention now.
- **operational_update** — relevant to ongoing work; read soon.
- **horizon_signal** — low current relevance, high future importance (the weak-signal quadrant).
- **archive** — neither relevant now nor strategically promising; keep but demote.

The rule (canonical):

- `relevance >= 5` → **immediate_priority**, *regardless of strategic_potential*. A maximally
  relevant item (e.g. a security advisory in our own stack) is never demoted just because it
  isn't "strategic".
- else `relevance >= 4` **and** `strategic_potential >= 3` → **immediate_priority**.
- else `relevance >= 3` → **operational_update**.
- else (`relevance <= 2`) `strategic_potential >= 4` → **horizon_signal**.
- else → **archive**.

<!-- END CANONICAL SCORING SECTION -->

## Acceptance criteria

- Each new `RawItem` yields a well-formed `EnrichedItem` with all five scores, summary,
  why-it-matters, connection-to-work, and recommended action.
- Priority classes match `compute_priority_class` exactly (verified by reusing it, not a copy).
- Ranking demotes high-hype items; hype is never added to the other scores.
- Fact and interpretation remain separate in the output; the source URL is preserved.

## Files likely to change

`backend/app/enrichment/`, `backend/app/models/` (`EnrichedItem`), wiring from storage,
`prompts/` (if templates need tightening), `backend/tests/`.

## Test plan

- Unit: enrichment maps a model response into an `EnrichedItem`; priority class is taken from
  `priority.py` (assert it calls the canonical function).
- Property: for sampled score tuples, the persisted priority class equals
  `compute_priority_class(relevance, strategic_potential)`.
- Ranking: a high-hype, high-relevance item ranks below an equivalent low-hype item.

## Agent constraints

- **Import `app/scoring/priority.py`; do not re-implement the rule.** Respect the hype inversion.
- Separate source fact from interpretation; preserve the source URL.
- One slice; stop at the review gate.

## Paste-ready agent prompt

> Implement Task 005 (llm-enrichment) per `tasks/005-llm-enrichment.md`. Enrich each new
> `RawItem` into an `EnrichedItem` using the `prompts/` templates: classification/tags, the five
> scores (hype inverted), summary, why-it-matters, connection-to-work, recommended action.
> Compute the priority class by **importing `app/scoring/priority.py`** — do not re-implement it —
> and make ranking treat hype as a demotion. Keep fact separate from interpretation and preserve
> source URLs. Add unit/property/ranking tests. Work on `feat/005-llm-enrichment`; stop at the
> review gate.
