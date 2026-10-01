# Task 010 (M7.5 — remediation) — Convergence cluster coherence + draft surface validity

**Status: DEFECT 1 DONE (at review gate, 2026-08-03) · DEFECTS 2 + 3 NOT STARTED** — raised by
[`docs/reviews/2026-07-25-m7.5-draft-review.md`](../docs/reviews/2026-07-25-m7.5-draft-review.md)
at the M7.5 review gate.

> **Defect 1 outcome (2026-08-03).** Implemented and verified on `data/dev_corpus.db` over
> 2026-07-14 → 2026-07-21. **The coherent-cluster path fired**, not the degradation: the quadrant's
> 84 converging items resolve to **30 distinct drivers** (confirming the review's diagnosis), and
> the largest shared-driver group is **12 items on `OpenAI`**. All acceptance criteria below are
> met. **Residual finding, escalated, not fixed here:** the largest group is a *hub*, so the draft
> is now mechanically coherent but still overstates ("Weak Signal of the Week: OpenAI") — driver
> **eligibility** is out of this task's scope. See [D-024](../docs/DECISIONS.md); needs a ruling.
> Related: [D-025](../docs/DECISIONS.md) shows the X hook truncation is caused by a 200-char lead
> URL, **not** by the cluster label — Defect 2 cannot be closed by trimming prose alone.

Task 009 shipped drafts that fail one of its own acceptance criteria — *"the thin/no-convergence case
degrades gracefully — **no false 'converging' claim**"*. This task closes that gap and two draft-surface
defects found in the same review. It is **remediation of M7.5, not new scope.**

## Goal

The Weak Signal piece may claim convergence **only** when multiple items converge on the **same
driving entity**. Every generated draft must be valid on the surface it targets.

## Context — the defect

`backend/app/digests/sections.py:206-208` selects weak-signal items by the **per-item** property
`it.convergence > 0` (this item's driver spans `>= GRAPH_MIN_SOURCES` sources). Items converging on
*different, unrelated* entities are collected into one "cluster" and presented as collective
convergence. `GraphSignal.driver` (`backend/app/scoring/graph_signals.py:58`) already names the
driving entity per item and is never used for grouping.

Observed on the 2026-07-21 run: 8 items, 1 of which supported the stated thesis; label taken from a
VentureBeat headline; "9 independent sources" was the union across 8 unrelated claims.

---

## Defect 1 — Cluster membership requires a shared driver (BLOCKER)

### Scope

- Group weak-signal candidates by `GraphSignal.driver` (normalised entity uid, not display name).
- The cluster is the **largest group** whose members share a driver, subject to a minimum size
  (`WEAK_CLUSTER_MIN_ITEMS`, default **2**) and the existing `>= GRAPH_MIN_SOURCES` distinct-source
  rule on that driver.
- `converged = True` **only** when such a group exists. Otherwise return the existing honest
  degradation path (`converged=False`) — the "quiet week" framing already implemented.
- Cluster **label** (`generator.py:_theme`) becomes the **driver entity name** when `converged`, not
  `items[0].title`. Keep the title fallback for the non-converged path.
- `_publishers()` must count only the sources backing **the shared driver**, not the union across
  all items. The "N independent sources" number must be defensible as sources for *one* claim.
- The cluster-level `why_it_matters` must be attributable. If the only available interpretation is
  the lead item's, either label it as such or omit it — do not present a single item's
  interpretation as the cluster's.

### Non-goals

- Do **not** modify `backend/app/scoring/priority.py` (standing ruling, D-014).
- Do **not** change `HORIZON_CLASSES`, thresholds, or any scoring calibration to make a cluster
  appear. If the honest answer is "no coherent cluster", ship that.
- No new graph queries, no re-projection, no Neo4j schema change — `driver` is already computed.
- No changes to enrichment or `prompts/classify_item.md`.

### Acceptance criteria

- A cluster of items with **different** drivers never yields `converged=True`.
- A cluster of items sharing a driver yields `converged=True`, is labelled with the **entity name**,
  and reports a source count derived from that driver alone.
- Replaying the 2026-07-21 corpus (`data/dev_corpus.db`, `--days 7`, 2026-07-14 → 2026-07-21)
  produces **either** a coherent cluster **or** the honest "quiet week" degradation — never the
  current 8-item incoherent cluster. Record which, in the run notes.
- Every source URL is preserved in the draft regardless of path (URL invariant).
- **Tier disclosure (required by D-016 ruling D).** When the cluster is drawn from `archive`-tier
  items rather than `horizon_signal`, the draft must **say so** in plain language and make no claim
  of top-tier provenance. An archive-sourced weak signal is permitted; an undisclosed one is not.

### Test plan

- `test_mixed_drivers_do_not_converge` — items with distinct drivers → `converged is False`.
- `test_shared_driver_converges` — ≥2 items sharing a driver → `converged is True`, label is the
  entity name.
- `test_cluster_label_is_entity_not_headline` — pins the regression: label must not equal
  `items[0].title` on the converged path.
- `test_publisher_count_scoped_to_driver` — a cluster with an off-driver item does not inflate the
  publisher count.
- `test_no_cluster_degrades_honestly` — empty/singleton case produces the "quiet week" wording and
  makes **no** converging claim.
- `test_archive_tier_cluster_is_disclosed` — a cluster built from `archive`-tier items produces a
  draft that states the tier (D-016 ruling D).

---

## Defect 2 — X thread items exceed the character limit

`generator.py:166-169` assembles thread items with no length check; only the hook passes through
`_fit_hook`. Observed: 9 thread items at 400–600 chars each.

### Scope

- Every emitted X thread item respects `X_CHAR_LIMIT`, trimming the variable portion while preserving
  the URL intact (reuse `_fit_hook`'s contract — do not write a second trimming rule).
- If a FACT cannot fit with its URL, prefer keeping the URL and truncating the prose.

### Acceptance criteria

- No emitted X thread item exceeds `X_CHAR_LIMIT`.
- Every source URL still appears somewhere in the X draft (URL invariant holds under truncation).

### Test plan

- `test_all_x_thread_items_within_limit` — parametrised over a long-summary fixture.
- `test_x_truncation_preserves_urls` — asserts URL set is unchanged after trimming.

---

## Defect 3 — Noise Report has no editorial cap

`2026-07-21-noise-report-medium.md` is 141 KB / 187 items. LinkedIn and X variants are 16 KB.

### Scope

- Cap the Noise Report at `NOISE_REPORT_LIMIT` (default **12**), loudest-first, on all three surfaces.
- State the true total honestly in the prose (e.g. "187 items were demoted this week; here are the
  12 loudest") — the cap must not misrepresent corpus size.

### Non-goals

- No change to `is_noise` or the hype threshold. This is presentation only.

### Acceptance criteria

- Each Noise Report draft contains at most `NOISE_REPORT_LIMIT` items.
- The full demoted count still appears in the text.
- Medium draft is under ~20 KB on the 2026-07-21 corpus.

### Test plan

- `test_noise_report_respects_limit`
- `test_noise_report_states_true_total`

---

## Files likely to change

`backend/app/digests/sections.py` · `backend/app/posts/generator.py` ·
`backend/app/core/config.py` (two new settings) · `backend/tests/`

## Out of scope (own task files)

AI-topicality gate in `classify_item.md` · MIT TR source-registry scope · D-013 orphaned backlog ·
D-014 M8 calibration · `docs/m7.5-broad-notes.md` correction.

---

## Agent prompts (paste-ready, one per session, review gate between)

### Session 1 — Defect 1 (cluster coherence)

```
Read HANDOFF.md, then CLAUDE.md, then docs/reviews/2026-07-25-m7.5-draft-review.md,
then tasks/010-convergence-cluster-coherence.md. All are binding.

Implement DEFECT 1 ONLY (cluster membership requires a shared driver).
Do not touch Defect 2 or 3 — they are separate sessions.

KEY FACTS (verified, do not re-derive):
- backend/app/digests/sections.py:206-208 filters on the PER-ITEM property
  `it.convergence > 0`, which collects items converging on DIFFERENT entities.
- backend/app/scoring/graph_signals.py:58 — `GraphSignal.driver` already names the
  driving entity per item. It is computed and never used for grouping. Use it.
  Group on the normalised entity uid, not the display name.
- backend/app/posts/generator.py:118-120 — `_theme()` returns items[0].title.
  On the converged path this must become the driver entity name.
- backend/app/posts/generator.py:72-80 — `_publishers()` unions contributing_sources
  across all items, inflating the "N independent sources" claim. Scope it to the
  sources backing the shared driver.

HARD CONSTRAINTS
- backend/app/scoring/priority.py is UNTOUCHABLE (standing ruling, D-014).
- Do NOT change HORIZON_CLASSES, GRAPH_MIN_SOURCES, or any threshold to make a
  cluster appear. If the honest answer on the real corpus is "no coherent cluster",
  that is a CORRECT result — ship the existing converged=False degradation.
- No new graph queries, no re-projection, no Neo4j changes.
- New settings go in backend/app/core/config.py with defaults; no magic numbers.
- No new abstractions (no ClusterStrategy class). One grouping function.

RULING IN FORCE (D-016 item D, 2026-08-03): an `archive`-tier weak signal IS
permitted — `horizon_signal` is empty for a known enrichment reason (D-018), fixed
separately under task 012. But the draft MUST state the tier honestly and claim no
top-tier provenance. Disclosure is an acceptance criterion, not a nicety.

TESTS (all six, names as written in the task file)
test_mixed_drivers_do_not_converge · test_shared_driver_converges ·
test_cluster_label_is_entity_not_headline · test_publisher_count_scoped_to_driver ·
test_no_cluster_degrades_honestly · test_archive_tier_cluster_is_disclosed

VERIFY ON REAL DATA
PREREQUISITE — the graph is almost certainly EMPTY. The 2026-07-21 run tore the
stores down with `down -v`, which removes the volumes. Convergence is read from
Neo4j, so `driver` will be empty for every item until the graph is rebuilt. Before
generating anything:
    docker compose -p m75broad -f docker-compose.m75.yml up -d
    PYTHONPATH=backend python -m app.cli graph-reindex
SQLite is the source of truth and Neo4j is a rebuildable derived index (ADR 0001),
so this is a safe rebuild, not a re-fetch — it costs no LLM spend.
Confirm the graph is populated BEFORE concluding anything about `driver`. An empty
graph is an environment state, not the defect you are fixing — do not confuse them.

Then run the digest + posts against data/dev_corpus.db for --days 7 over
2026-07-14 → 2026-07-21. NOTE: with a relative DATABASE_URL the CLI must be run from
the REPO ROOT with PYTHONPATH=backend (per D-006) — docs/m7.5-broad-notes.md has the
wrong recipe, do not follow it. Report which path fired (coherent cluster vs honest
degradation) and paste the regenerated weak-signal LinkedIn hook line.

ACCEPTANCE
- Full backend suite green (baseline: 174 passed, 1 skipped, 0 failed) + 6 new tests.
- Regenerated drafts no longer contain the 8-item incoherent cluster.
- Every source URL preserved on both paths.
- CHANGELOG.md entry.
- Append a D-NNN entry to docs/DECISIONS.md for every choice made without asking
  (per CLAUDE.md session protocol), and overwrite HANDOFF.md at session end.

STOP CONDITIONS — report instead of improvising:
- If `driver` is empty/None for most weak-signal items AFTER a successful
  graph-reindex, STOP and report. That would mean the graph signal is not populated
  as expected and changes the whole approach. (Before the reindex, empty is normal —
  see the prerequisite above.)
- If grouping leaves zero clusters ≥ 2 items on the real corpus, that is a valid
  result — implement it, ship the honest degradation, and say so plainly. Do not
  lower the minimum to manufacture a cluster.
```

### Session 2 — Defects 2 + 3 (draft surface validity)

```
Read HANDOFF.md, CLAUDE.md, and tasks/010-convergence-cluster-coherence.md.
Defect 1 is done and reviewed.

Implement DEFECT 2 (X thread character limit) and DEFECT 3 (Noise Report cap).
These are presentation-only. No scoring, no selection, no enrichment changes.

DEFECT 2 — backend/app/posts/generator.py:166-169 emits thread items with no length
check; only the hook goes through _fit_hook. Route every thread item through the same
trimming contract. Do NOT write a second trimming rule. If a FACT cannot fit with its
URL, keep the URL and truncate the prose.

DEFECT 3 — Cap the Noise Report at NOISE_REPORT_LIMIT (new setting, default 12),
loudest-first, on X / LinkedIn / Medium. The prose must still state the TRUE total
("187 items were demoted this week; here are the 12 loudest"). The cap must never
misrepresent corpus size. Do not change is_noise or the hype threshold.

TESTS
test_all_x_thread_items_within_limit · test_x_truncation_preserves_urls ·
test_noise_report_respects_limit · test_noise_report_states_true_total

ACCEPTANCE
- Full suite green. Regenerated Medium noise report under ~20 KB on the 2026-07-21
  corpus. No X item over the limit. All source URLs preserved.
- CHANGELOG.md entry; D-NNN entries in docs/DECISIONS.md; HANDOFF.md overwritten.
```
