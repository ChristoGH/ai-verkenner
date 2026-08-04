# Task 013 — Driver eligibility: the weak signal must be the *quietest* corroborated entity

**Status: NOT STARTED** — raised by [D-024](../docs/DECISIONS.md) at the Task 010 review gate,
ruled by [D-026](../docs/DECISIONS.md).

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
