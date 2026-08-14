# Task 017 — Wire `docs/USER_CONTEXT.md` into the runtime

**Status: NOT STARTED** — raised by Task 015's revert ([D-062](../docs/DECISIONS.md)),
authorised by [D-069](../docs/DECISIONS.md).

> **Run this BEFORE the fresh ingest.** Every enrichment call bills against whatever `user_context`
> is in force. Ingesting ~100 new items first means paying to score them against a placeholder and
> then wanting them re-scored.

## Goal

The `relevance` axis is scored against Christo's **actual** work, not a 309-character stub.

## Context — the defect

`docs/USER_CONTEXT.md` opens by describing itself as *"the ground truth AI Verkenner uses to score
`relevance` and `connection_to_user_work`"* and *"the cheapest lever on output quality"*.

**It is referenced in no Python file in the repository.** `USER_CONTEXT` is unset, so
`backend/app/core/config.py:139-145` falls back to its literal default:

> "A solo engineer building AI Verkenner: a personal AI intelligence and early-warning system.
> Stack: Python, FastAPI, SQLite, Qdrant, Neo4j, React/TypeScript, local sentence-transformers
> embeddings, **and a cloud LLM**. Interests: LLM tooling, RAG, vector/graph databases, agentic
> systems, and AI developer tooling."

Compare what `docs/USER_CONTEXT.md` actually contains: **ARQ Platform** (25+ containerised apps on
AKS with Knative scale-to-zero, hybrid Qdrant + SQLite, **open decision: Lakebase pgvector vs
Qdrant**) · **repo_ingest** (tree-sitter chunking, Voyage/OpenAI embeddings, incremental git-diff)
· **Commission Intelligence** (Qdrant + Neo4j + spaCy + **Claude SDK** + React) · **MedVoice**
(Firebase Auth, Cloud Run, Google STT, Claude, healthcare compliance) · **BellBook** (Clickatell,
Paystack/Ozow) · **SmartSolar** (Sunsynk).

The stub names **no vendor and no open decision**. So an Anthropic model release, an Agent SDK
change, a pgvector-versus-Qdrant benchmark, or a tree-sitter parser update — each of which should be
a top-of-scale relevance item — scores low, correctly, against the context it was actually given.

**This is why Task 015 failed.** D-062 established that the rewritten anchors worked as written and
correctly returned "no" on all 45 items. The anchors were never the binding constraint. Three
billable calibration runs ($1.42 + $1.62 + $1.73 = **$4.77**) were spent tuning prompt wording
against a context that could not support the answer.

## Scope

1. **Load the file.** New setting `USER_CONTEXT_PATH`, defaulting to `docs/USER_CONTEXT.md`,
   resolved through the **same configurable base-path mechanism `prompts/` and `sources/` already
   use** — do not hardcode a path, and do not introduce a second resolution convention.
2. **Precedence, explicitly:** an explicit `USER_CONTEXT` env value wins (so a run can override for
   an experiment) → else the file at `USER_CONTEXT_PATH` → else the existing literal default.
   Never silently fall through: **log which source was used, once, at startup.** A silent fallback
   to the stub is exactly the failure this task exists to fix, and it must not be able to recur
   unobserved.
3. **Decide what to send.** The whole document may be larger than the scoring call needs. Report the
   character and token count of the full file, and if a section is plainly not scoring-relevant, say
   so and propose a boundary — but **do not trim on your own judgement** without reporting it.
4. **Measure the cost delta.** The context is resent on every enrichment call. Report tokens added
   per call and the projected per-item and per-100-item cost increase, against the measured baseline
   of ~$0.036/item for classify.

## Non-goals

- **No prompt wording changes.** `prompts/classify_item.md` and `fallback.py` stay exactly as
  committed at Task 012 attempt 2. This task changes *what context is supplied*, not how it is
  interpreted. Confounding the two is why this is a separate task.
- `backend/app/scoring/priority.py` untouchable (D-014).
- No new axes, no renaming, no change to the hype inversion.
- No editing of `docs/USER_CONTEXT.md`'s content — wire it in as it stands. Its accuracy is
  Christo's to maintain (the file says so itself).
- No full-corpus re-enrichment. Sample only.

## Acceptance criteria

- The runtime demonstrably uses `docs/USER_CONTEXT.md`; startup log names the source in force.
- Re-run **the same 45 items** (identity verified before spending), prompts unchanged:
  - **At least one item reaches `relevance >= 4`.** This is the criterion Task 015 could not meet.
  - **Task 012's gates hold:** quadrant occupancy `>= 1`, `sp >= rel + 2` count `>= 3`.
  - Report `actionability >= 4` count — informational, not a gate.
- **Named prediction, stated before the run:** items about Claude / Anthropic / the Agent SDK,
  pgvector-vs-Qdrant, tree-sitter, or Knative should rise on `relevance`. Report whether they did.
  **If they did not, that is the most interesting result of the run** — say so plainly rather than
  reporting a null.
- No inflation: per-axis means before and after; 10-item hand spot-check with misses named.
- `r(relevance, strategic_potential)` reported as a diagnostic, not gated (D-057). It will likely
  rise; that is expected.
- Cost recorded, including the context-size delta.

## Test plan

- `test_user_context_loads_from_file` — the configured file is read and reaches the enricher.
- `test_explicit_env_overrides_file` — precedence order holds.
- `test_missing_file_falls_back_and_logs` — absent file → default, and the fallback is **logged**,
  not silent.
- `test_user_context_path_uses_existing_base_path_convention` — pins that no second path convention
  was introduced.

## Files likely to change

`backend/app/core/config.py` · wherever `prompts/` and `sources/` base paths are resolved ·
`docs/m8-calibration-notes.md` (append) · `backend/tests/`

## What happens after this

- If `relevance >= 4` becomes reachable, **Task 015 may be unnecessary** — its premise was that the
  anchors were wrong. Re-read 015 against this result before re-running anything; D-062 already says
  not to run it as written.
- Then, and only then, the fresh ingest.

---

## Agent prompt (paste-ready)

```
Read HANDOFF.md, then CLAUDE.md, then docs/AGENT_ADDENDUM.md, then docs/DECISIONS.md
entry D-062, then docs/m8-calibration-notes.md § Task 015, then
tasks/017-wire-user-context.md. All binding.

THE DEFECT (verified, do not re-derive)
docs/USER_CONTEXT.md calls itself "the ground truth AI Verkenner uses to score
relevance" and "the cheapest lever on output quality". It is referenced in NO Python
file. USER_CONTEXT is unset, so config.py:139-145 uses its 309-character literal
default, which says "...and a cloud LLM" — naming no vendor and no open decision.

Meanwhile the real file names ARQ Platform (AKS, Knative, Qdrant+SQLite, OPEN DECISION:
Lakebase pgvector vs Qdrant), repo_ingest (tree-sitter, Voyage/OpenAI embeddings),
Commission Intelligence (Qdrant+Neo4j+spaCy+Claude SDK+React), MedVoice, BellBook,
SmartSolar.

So an Anthropic release, an Agent SDK change, or a pgvector-vs-Qdrant benchmark scores
LOW — correctly, against the context it was actually given. This is why task 015 failed
(D-062): the anchors worked as written and correctly said "no". $4.77 across three runs
was spent tuning wording against a context that could not support the answer.

IMPLEMENT
1. New setting USER_CONTEXT_PATH defaulting to docs/USER_CONTEXT.md, resolved through
   THE SAME configurable base-path mechanism prompts/ and sources/ already use. Do not
   hardcode a path. Do not invent a second resolution convention.
2. Precedence: explicit USER_CONTEXT env value > file at USER_CONTEXT_PATH > existing
   literal default. LOG WHICH SOURCE IS IN FORCE at startup, once. A silent fallback to
   the stub is precisely the failure this task exists to fix — it must not be able to
   recur unobserved.
3. Report the full file's character and token count. If some section is plainly not
   scoring-relevant, SAY SO and propose a boundary — do NOT trim on your own judgement
   without reporting it.
4. Report the cost delta: tokens added per call, projected per-item and per-100-item
   increase against the measured ~$0.036/item classify baseline.

HARD CONSTRAINTS
- NO prompt wording changes. prompts/classify_item.md and fallback.py stay exactly as
  committed at task 012 attempt 2. This task changes WHAT CONTEXT IS SUPPLIED, not how
  it is interpreted — confounding the two is why it is a separate task.
- Do NOT edit docs/USER_CONTEXT.md's content. Wire it in as it stands.
- priority.py UNTOUCHABLE (D-014). No new axes, no renaming, no hype-inversion change.
- Sample only. Full-corpus re-enrichment is NOT authorised.

MEASURE: the SAME 45 items, identity verified before spending, prompts unchanged.
APPEND to docs/m8-calibration-notes.md — all prior runs stay on the record.

STATE THIS PREDICTION BEFORE YOU RUN, then report against it: items about Claude /
Anthropic / Agent SDK, pgvector-vs-Qdrant, tree-sitter or Knative should RISE on
relevance. IF THEY DO NOT, that is the most interesting result of the run — say so
plainly. Do not bury it as a null.

COST GATE: ~$2.00 approved for one 45-item sample (higher than prior runs because the
context is larger). If it overruns, record the actual figure as a D-NNN entry rather
than absorbing it — as D-055 and D-063 did.

ACCEPTANCE
- Runtime demonstrably uses docs/USER_CONTEXT.md; startup log names the source.
- >= 1 item reaches relevance >= 4 (the criterion task 015 could not meet).
- Task 012's gates HOLD: quadrant occupancy >= 1, sp >= rel + 2 count >= 3.
- No inflation: means before/after, 10-item hand spot-check with misses named.
- Suite green — re-verify the baseline yourself (D-022).

STOP CONDITIONS
- One sample run. If relevance >= 4 is still unreachable under the real context, STOP
  and report. Do not iterate, and do not start editing anchors — that is task 015, it
  is reverted, and D-062 says not to re-run it as written. Four billable runs on this
  question is enough; the next move would be Christo's.
- If wiring the file requires changing how prompts/ or sources/ resolve their paths,
  STOP and report rather than refactoring a working convention.

Check the highest D-NNN in docs/DECISIONS.md before appending — concurrent sessions have
collided before. Merge into HANDOFF.md rather than overwriting other sessions' entries.
```
