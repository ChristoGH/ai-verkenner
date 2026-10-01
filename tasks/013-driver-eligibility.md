# Task 013 — Driver eligibility: the weak signal must be the *quietest* corroborated entity

**Status: DEFECTS A + B + C ALL IMPLEMENTED — at the review gate (2026-08-04).**
Raised by [D-024](../docs/DECISIONS.md) at the Task 010 review gate, ruled by
[D-026](../docs/DECISIONS.md), amended by [D-047](../docs/DECISIONS.md). Decisions D-031…D-036
(attempt 1) and D-051…D-052 (attempt 2) recorded. Do not self-merge (CLAUDE.md).

> **Attempt 2 outcome (2026-08-04) — Defect C done, floor in force.** `WEAK_DRIVER_MIN_SOURCES`
> (new, default 3) and `WEAK_CLUSTER_MIN_ITEMS` (2 → 3) are selection-only; `GRAPH_MIN_SOURCES`
> stays at 2 and a test proves convergence scoring is unaffected. On the 2026-07-14 → 07-21 window
> the winner is **`Claude Code` — 5 mentions / 4 distinct sources / 3 items**, quietest of **5
> eligible** groups of 30. `Firefox` is excluded. Suite **218 passed / 1 skipped / 0 failed**; nine
> fixtures built at the old floor were **raised to it, not exempted** ([D-051]). One residual
> finding: the third cluster item references the driver only in passing ([D-052]) — a mention-weight
> question, out of this task's scope.

> **Review outcome (2026-08-04) — the objective is right, the floor is too low.**
> The swap works exactly as intended: `OpenAI` (17 mentions / 12 items) now sorts last and the
> stoplist correctly excludes the AI/LLM concept family. But the winner was **`Firefox` — 2 mentions,
> 2 distinct sources, 2 items**, with **three groups tied** at that same floor.
>
> `GRAPH_MIN_SOURCES = 2` and `WEAK_CLUSTER_MIN_ITEMS = 2` (`backend/app/core/config.py:153,174`), so
> *minimising* ambient volume bottoms out at the corroboration floor **by construction**. Two sources
> mentioning something twice is statistically indistinguishable from coincidence — and D-036 confirms
> it empirically: one of Firefox's two items is a Mozilla release-cadence story with no AI content.
> The three-way tie broken by `graph_score` is the same symptom.
>
> A weak signal needs **enough corroboration to be real AND low ambient volume**. Attempt 1 delivered
> only the second half. **Defects A and B are accepted and stay as implemented — do not revert them.**
> Defect C below adds the missing half.

**Result on 2026-07-14 → 07-21:** the selected driver is **`Firefox`** — mentions **2**, distinct
sources **2**, group size **2** — the quietest of **12 eligible** groups out of **30** shared-driver
groups. `OpenAI` (17 mentions / 12 items) sorts last; `AI`, `LLM`, `LLMs`, `Large language models`
and `Artificial Intelligence` are excluded as stoplisted concepts. Hook: *"The AI signal most feeds
will miss this week: Firefox is quietly converging across 2 independent sources."* Tier disclosure
(archive) fires on all three surfaces; every source URL preserved. See [D-036](../docs/DECISIONS.md)
for the finding on that cluster's topicality, and `CHANGELOG.md` for the full record.

**Sequencing: this task must merge BEFORE [Task 014](014-entity-normalisation.md).** Normalising
entity aliases first would merge "AI" / "LLM" / "LLMs" / "Large language models" into one *larger*
hub and make the defect below worse, not better.

## Goal

The Weak Signal of the Week names the **quietest entity that multiple independent sources
nonetheless touched** — never the loudest entity in the corpus, and never a generic concept node.

## Context — the objective function is inverted

Task 010 Defect 1 correctly made cluster membership require a shared `driver_uid`. But the
*selection* rule it was given — implemented at `backend/app/digests/sections.py`,
`coherent_cluster()` — is:

```python
key=lambda kv: (len(kv[1]), sum(it.graph_score for it in kv[1]), -kv[0])
```

**Largest group wins.** A weak signal is by definition *corroborated but not yet loud*, so
maximising group size selects for exactly the wrong property. Measured on 2026-07-14 → 07-21
(D-024): 185 quadrant items, 84 with `convergence > 0`, resolving to **30 distinct drivers**, with a
hub-shaped distribution —

| driver | items |
|---|---|
| OpenAI | 12 |
| Large language models | 7 |
| Microsoft | 7 |
| Google | 7 |
| AI | 6 |
| LLM | 5 |
| fine-tuning | 4 |

17 groups reach ≥2; 13 drivers are singletons. "Largest wins" selected **OpenAI**, producing the hook
*"OpenAI is quietly converging across 7 independent sources"* — self-refuting. M5.5's IDF dampening
does not prevent this: OpenAI spans 18 of ~246 developments, so its IDF is still ~2.6 and its 7
distinct sources dominate the product.

This is a **specification defect**, not an implementation defect. Task 010's code does exactly what
it was told.

---

## Defect A — Select the quietest eligible driver, not the largest group

### Scope

- Among groups that clear the corroboration bar — `len(group) >= WEAK_CLUSTER_MIN_ITEMS`, and
  `convergence > 0` (which already guarantees `>= GRAPH_MIN_SOURCES` distinct sources) — select the
  driver with the **lowest ambient corpus volume**.
- Ambient volume = the driver entity's total mention count over the convergence window, already
  available from the graph convergence read (`store.convergence(since)` exposes distinct sources,
  mentions and degree — D-015 reports them per entity). **Do not add a new graph query**; if the
  figure is not already carried through to `DigestItem`, thread the existing value rather than
  re-querying.
- Tie-break, in order: lower mentions → larger group size → higher summed `graph_score` → lower uid.
  Selection must be deterministic and stable.
- Surface the chosen driver's stats (mentions, distinct sources, group size) in the run output so the
  choice is auditable.

### Non-goals

- **Do not change the convergence maths.** IDF dampening, `GRAPH_MIN_SOURCES`, and
  `graph_signals.py` scoring stay as they are. This task changes *which group is chosen*, not how
  convergence is computed.
- `backend/app/scoring/priority.py` remains untouchable (D-014).
- No entity normalisation — Task 014, and it must come after this.
- No new abstractions. This is a change to one sort key plus an eligibility filter.

---

## Defect B — Generic concept nodes are never eligible drivers

"AI", "LLM", "LLMs", "Large language models", "Artificial Intelligence", "machine learning" are the
*category*, not entities within it. A cluster whose only shared driver is the category is the
original M7.5 defect wearing a better label — the eight-item incoherent cluster shared a generic
"LLM" hub, which is precisely how it passed.

### Scope

- A configurable stoplist of ineligible driver names (`WEAK_DRIVER_STOPLIST`), matched
  case-insensitively against the normalised driver identity.
- Seed it with at minimum: `ai`, `artificial intelligence`, `llm`, `llms`, `large language model`,
  `large language models`, `machine learning`, `ml`, `deep learning`, `neural network`,
  `generative ai`, `genai`, `model`, `models`.
- Stoplisted drivers are excluded from **selection**, not from the graph or from scoring. Nothing is
  deleted; they simply cannot be the face of a weak signal.
- Keep the list in config where a human can edit it without touching code, and comment why each
  class of term is there.

### Non-goals

- No IDF-threshold heuristic *instead of* the stoplist — an explicit, auditable list is preferred
  over a tuned number for a first pass. (The quietness ordering in Defect A already demotes hubs;
  the stoplist is the hard floor.)
- No fuzzy matching, no embeddings, no ML-based entity typing.

---

---

## Defect C — Raise the eligibility floor before minimising (ADDED 2026-08-04, D-047)

### The problem

Selection minimises ambient mention count among groups that clear the corroboration bar. That bar is
currently `>= 2 distinct sources` and `>= 2 items` — the lowest values that are not "one". So the
minimiser reliably lands on entities with the *thinnest possible evidence*, which is where
coincidence lives. Firefox at 2/2/2 is not an unlucky draw; it is the fixed point of the rule.

### Scope

- Add a **separate, higher eligibility floor for weak-signal selection**:
  - `WEAK_DRIVER_MIN_SOURCES` — new setting, **default 3**. A driver must span at least this many
    distinct sources to be *selectable* as the weak signal.
  - `WEAK_CLUSTER_MIN_ITEMS` — raise the **default from 2 to 3**.
- **Do NOT change `GRAPH_MIN_SOURCES`.** It is the global floor inside `graph_signals` below which a
  convergence contribution is zeroed; raising it would alter convergence scoring across the whole
  product, which Task 013's non-goals forbid and D-026 explicitly ruled out. The new floor applies to
  **selection only**, exactly like the stoplist.
- Both settings env-overridable and commented with *why* the value is 3: two sources mentioning
  something twice is not distinguishable from coincidence.
- The tie-break chain is unchanged — lower mentions → larger group → higher summed `graph_score` →
  lower uid. It should simply have far fewer ties to resolve once the floor rises.

### Expected effect (from the attempt-1 distribution)

With the stoplist applied and a floor of 3 items, the eligible set becomes: `OpenAI` 12 ·
`Microsoft` 7 · `Google` 7 · `fine-tuning` 4 · `Claude Code` 3. Quietest of those should be
`fine-tuning` or `Claude Code` — both defensible as "the signal most feeds will miss", neither a hub,
neither coincidence. **This is an expectation, not a requirement**: report what actually wins.

### Non-goals

- No change to `GRAPH_MIN_SOURCES`, IDF dampening, or any convergence maths.
- No change to Defects A or B. The objective stays *quietest*; the stoplist stays.
- No topicality gate on cluster items — D-036's Mozilla item is corpus scope, fixed by Task 011.
- `priority.py` remains untouchable (D-014).

---

## Acceptance criteria

- Replaying 2026-07-14 → 2026-07-21 selects a driver that is **neither** a stoplisted concept
  **nor** one of OpenAI / Microsoft / Google. Report the winning driver with its mentions, distinct
  sources and group size.
- A 3-item cluster on a low-mention driver beats a 12-item cluster on a hub driver.
- If **no** eligible group survives, the honest "quiet week" degradation ships and **no** converging
  claim is made. This is a correct outcome, not a failure.
- Selection is deterministic — the same corpus and window yield the same driver every run.
- Tier disclosure from D-016 (D) still applies and still passes.
- Every source URL preserved (URL invariant).
- Full backend suite green against the current baseline. **Re-verify the baseline; do not trust the
  recorded number** — D-022 found it was date-dependent.

## Test plan

- `test_quietest_eligible_driver_wins` — small low-mention cluster beats a large hub cluster.
- `test_concept_nodes_are_ineligible_drivers` — a stoplisted driver is never selected even when it
  is the only multi-item group.
- `test_min_items_still_enforced` — eligibility does not bypass `WEAK_CLUSTER_MIN_ITEMS`.
- `test_all_candidates_ineligible_degrades_honestly` — everything stoplisted → quiet-week path, no
  converging claim.
- `test_driver_selection_is_deterministic` — repeated runs, identical result; ties resolve stably.

**Added for Defect C:**

- `test_floor_excludes_thin_evidence_drivers` — a 2-source / 2-item driver is **not** selectable even
  when it is the quietest candidate; pins the Firefox regression by name.
- `test_quietest_above_floor_wins` — given one driver at 3 sources / 3 items / low mentions and
  another at 7 sources / 12 items / high mentions, the former wins.
- `test_graph_min_sources_unchanged` — asserts `GRAPH_MIN_SOURCES` is untouched and that the
  selection floor is a *separate* setting, so convergence scoring is provably unaffected.

## Files likely to change

`backend/app/digests/sections.py` · `backend/app/core/config.py` · `backend/tests/`

---

## Agent prompt (paste-ready)

```
Read HANDOFF.md, then CLAUDE.md, then docs/AGENT_ADDENDUM.md, then docs/DECISIONS.md
entries D-024 and D-026, then tasks/013-driver-eligibility.md. All binding.

CONTEXT YOU MUST UNDERSTAND BEFORE CODING
Task 010 made weak-signal cluster membership require a shared driver_uid — that part
is correct and stays. The defect now is the SELECTION rule in
backend/app/digests/sections.py :: coherent_cluster(), which picks the LARGEST group:

    key=lambda kv: (len(kv[1]), sum(it.graph_score for it in kv[1]), -kv[0])

A weak signal is CORROBORATED BUT NOT YET LOUD, so maximising group size optimises for
the opposite of the product's definition. On the real corpus it selected OpenAI (12
items, the loudest entity), producing "OpenAI is quietly converging across 7
independent sources" — self-refuting.

IMPLEMENT BOTH DEFECTS IN THE TASK FILE:
A. Among groups clearing the bar (len >= WEAK_CLUSTER_MIN_ITEMS; convergence > 0
   already guarantees >= GRAPH_MIN_SOURCES), select the driver with the LOWEST ambient
   mention count over the convergence window. Tie-break: lower mentions -> larger group
   -> higher summed graph_score -> lower uid. Deterministic and stable.
   The mention count already exists in the graph convergence read (see D-015: entities
   report distinct sources / mentions / degree). THREAD THE EXISTING VALUE — do not add
   a new graph query.
B. A configurable WEAK_DRIVER_STOPLIST makes generic concept nodes ineligible as
   drivers: ai, artificial intelligence, llm, llms, large language model(s), machine
   learning, ml, deep learning, neural network, generative ai, genai, model, models.
   Case-insensitive on the normalised identity. Excluded from SELECTION only — nothing
   is deleted from the graph or from scoring.

HARD CONSTRAINTS
- Do NOT change convergence maths: IDF dampening, GRAPH_MIN_SOURCES, graph_signals.py
  scoring all stay. You are changing WHICH GROUP IS CHOSEN, not how convergence works.
- backend/app/scoring/priority.py is UNTOUCHABLE (D-014).
- No entity normalisation — that is task 014 and it must come AFTER this one.
- No new abstractions. One sort key and one eligibility filter.
- Keep the stoplist in config, human-editable, commented.

VERIFY ON REAL DATA
The graph is POPULATED — 2130 nodes / 3666 rels / 246 Events as of the Task 010
session. (An earlier prompt claimed `down -v` had emptied it; that was false — D-023.
Check the graph, do not assume its state either way.) Bring the stores up; re-run
`PYTHONPATH=backend python -m app.cli graph-reindex` only if the graph is actually
empty — it is a free rebuild from SQLite (ADR 0001), but not needed if populated.

Note D-023: there is no `--now` / as-of flag on `app.cli digest|posts`, so a historical
window is not reproducible from the CLI. The Task 010 session called
`build_digest_data` directly to reproduce 2026-07-14 16:28 -> 2026-07-21 10:45. Do the
same, and say which method you used.

Report the winning driver with its mentions / distinct sources / group size, and paste
the regenerated weak-signal LinkedIn hook line.

TESTS: the five named in the task file.

ACCEPTANCE
- The selected driver is neither stoplisted nor OpenAI/Microsoft/Google.
- Full backend suite green. RE-VERIFY THE BASELINE COUNT — do not trust the recorded
  number; D-022 found the fixtures were date-dependent and would fail at month end.
- Tier disclosure (D-016 D) still passes. All source URLs preserved.
- CHANGELOG.md entry; D-NNN entries for every unasked choice; overwrite HANDOFF.md.

STOP CONDITIONS — report, do not improvise:
- If NO eligible group survives on the real corpus, that is a CORRECT result. Ship the
  honest quiet-week degradation and say so plainly. Do NOT trim the stoplist, lower
  WEAK_CLUSTER_MIN_ITEMS, or widen eligibility to manufacture a cluster.
- If the mention count is not already threaded through to the digest layer and reaching
  it would require a new graph query, STOP and report rather than adding one.
```

---

## Agent prompt — ATTEMPT 2 (Defect C only) · paste-ready

```
Read HANDOFF.md, then CLAUDE.md, then docs/AGENT_ADDENDUM.md, then docs/DECISIONS.md
entries D-026, D-036 and D-047, then tasks/013-driver-eligibility.md. All binding.

Task 013 Defects A and B are IMPLEMENTED AND ACCEPTED. Do NOT revert or rework them.
Implement DEFECT C ONLY.

WHAT WENT WRONG IN ATTEMPT 1
Selection minimises ambient mention count among groups clearing the corroboration bar.
That bar is GRAPH_MIN_SOURCES = 2 and WEAK_CLUSTER_MIN_ITEMS = 2
(backend/app/core/config.py:153,174) — the lowest values that are not "one". So the
minimiser lands on the thinnest possible evidence by construction. It selected Firefox:
2 mentions / 2 distinct sources / 2 items, with THREE groups tied at that floor, and
D-036 confirms one of the two items has no AI content at all. Firefox was not bad luck;
it is the fixed point of the rule.

A weak signal needs ENOUGH CORROBORATION TO BE REAL **and** LOW AMBIENT VOLUME.
Attempt 1 delivered only the second half.

IMPLEMENT
- New setting WEAK_DRIVER_MIN_SOURCES, default 3: a driver must span at least this many
  DISTINCT SOURCES to be selectable as the weak signal.
- Raise WEAK_CLUSTER_MIN_ITEMS default from 2 to 3.
- Both env-overridable, both commented with WHY 3 (two sources mentioning something
  twice is not distinguishable from coincidence).
- Tie-break chain unchanged: lower mentions -> larger group -> higher summed
  graph_score -> lower uid.

HARD CONSTRAINTS
- DO NOT CHANGE GRAPH_MIN_SOURCES. It is the global floor inside graph_signals below
  which a convergence contribution is zeroed. Raising it would alter convergence
  scoring product-wide — forbidden by this task's non-goals and by D-026. The new floor
  is a SELECTION-ONLY filter, exactly like the stoplist. Add a test proving
  GRAPH_MIN_SOURCES is untouched.
- No change to Defects A or B. Objective stays "quietest"; stoplist stays.
- No topicality gate on cluster items — D-036's Mozilla item is corpus scope and is
  Task 011's job, not this one.
- priority.py remains untouchable (D-014).

TESTS: the three named under "Added for Defect C" in the task file. Keep the six
existing ones green.

VERIFY ON REAL DATA
Graph is populated (2130 nodes / 3666 rels) — check, don't assume, and reindex only if
actually empty. There is no --now flag (D-023), so reproduce the window by calling
build_digest_data directly as attempt 1 did: period_days=7, now=2026-07-21 10:45Z.
Report the winning driver with mentions / distinct sources / group size, the full
eligible set after the floor, and the regenerated weak-signal LinkedIn hook line.

EXPECTATION, NOT REQUIREMENT: from attempt 1's distribution the eligible set should
become OpenAI 12 / Microsoft 7 / Google 7 / fine-tuning 4 / Claude Code 3, so the winner
should be fine-tuning or Claude Code. Report what ACTUALLY wins — if it differs, that is
data, not failure.

ACCEPTANCE
- No 2-source or 2-item driver is selectable.
- Full backend suite green. RE-VERIFY the baseline count yourself; the tree currently
  holds several sessions' interleaved work, so do not trust any recorded number (D-022).
- Tier disclosure (D-016 D) still passes; all source URLs preserved.
- CHANGELOG.md entry; D-NNN entries for unasked choices; merge your status into
  HANDOFF.md rather than overwriting other sessions' entries.

STOP CONDITIONS — report, do not improvise:
- If NO group clears the raised floor on the real corpus, that is a CORRECT result.
  Ship the honest quiet-week degradation and say so. Do NOT lower the floor, trim the
  stoplist, or widen eligibility to manufacture a cluster. An honest empty week is the
  product working.
- If another session is mid-write in this tree, coordinate decision numbers before
  appending to docs/DECISIONS.md — D-028..D-036 already collided once.
```
