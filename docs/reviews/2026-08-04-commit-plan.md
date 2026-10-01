# Commit plan — separating four interleaved sessions (2026-08-04)

Four sessions wrote this working tree concurrently (Task 010 S2, 011, 012, 013 Defect C). Every one
is reviewed and accepted, but the tree is one undifferentiated diff. `CLAUDE.md` requires one slice
at a time; a single blanket commit would make all four unbisectable and unrevertable.

**This is the immediate blocker on everything else.** Nothing new should start until it is done.

## Intended commits, in dependency order

| # | Task | Scope |
|---|---|---|
| 1 | **010 Defects 2 + 3** | X character limits (`_fit_x`, `_thread`), Noise Report cap |
| 2 | **011** | Source scope + fetch health |
| 3 | **013 Defect C** | Selection floors — depends on 010 S1, already committed in `4b792c8` |
| 4 | **012** | Enrichment calibration — prompt-only, independent |
| 5 | **docs** | `HANDOFF.md`, tasks 015/016, review docs, remaining `DECISIONS.md` |

## The shared files — these need hunk-level staging

These are touched by more than one task and **cannot** be staged whole:

- `backend/app/core/config.py` — `NOISE_REPORT_LIMIT` (010) · `SOURCE_ZERO_YIELD_WARN` (011) ·
  `WEAK_DRIVER_MIN_SOURCES` + `WEAK_CLUSTER_MIN_ITEMS` (013)
- `docs/DECISIONS.md` — split by D-number: D-028…D-030 (010 S2) · D-037…D-041, D-050 (011) ·
  D-031…D-036, D-047, D-051, D-052 (013) · D-042…D-046, D-049, D-053…D-055 (012) · D-048, D-056,
  D-057 (docs)
- `CHANGELOG.md` — split by task
- `HANDOFF.md` — commit **once**, last

---

## Agent prompt (paste-ready)

```
Read HANDOFF.md, then CLAUDE.md, then docs/AGENT_ADDENDUM.md, then
docs/reviews/2026-08-04-commit-plan.md. All binding.

TASK: separate this working tree into five commits on feat/m7.5-broad-run. This is
GIT SURGERY ONLY — do not write, fix, refactor or improve any code. If you notice a
defect, note it in your report and leave it alone.

CONTEXT: four sessions (Task 010 S2, 011, 012, 013 Defect C) wrote this tree
concurrently. All four are reviewed and ACCEPTED. A blanket commit would make them
unbisectable and unrevertable, which CLAUDE.md's one-slice-at-a-time rule exists to
prevent.

BEFORE ANYTHING: `rm -f .git/index.lock` if a stale lock is present (a sandboxed
session created one earlier — see AGENT_ADDENDUM §7). Confirm no git process is
actually running first. Then record `git status --short` and the current test count as
your starting point.

COMMIT IN THIS ORDER (the plan file lists the scope of each):
1. Task 010 Defects 2+3 — X char limits + Noise Report cap
2. Task 011 — source scope + fetch health
3. Task 013 Defect C — selection floors
4. Task 012 — enrichment calibration (prompt-only)
5. Docs — HANDOFF.md, tasks/015, tasks/016, docs/reviews/, remaining DECISIONS.md

SHARED FILES NEEDING `git add -p` (hunk-level, NOT whole-file):
- backend/app/core/config.py — NOISE_REPORT_LIMIT (010) / SOURCE_ZERO_YIELD_WARN (011)
  / WEAK_DRIVER_MIN_SOURCES + WEAK_CLUSTER_MIN_ITEMS (013)
- docs/DECISIONS.md — by D-number: D-028..D-030 -> commit 1; D-037..D-041 + D-050 ->
  commit 2; D-031..D-036 + D-047 + D-051 + D-052 -> commit 3; D-042..D-046 + D-049 +
  D-053..D-055 -> commit 4; D-048 + D-056 + D-057 -> commit 5
- CHANGELOG.md — split by task
- HANDOFF.md — commit 5 only, whole file

METHOD
- Verify each commit's content with `git diff --cached` BEFORE committing. If a hunk is
  ambiguous, STOP and ask rather than guessing which task owns it.
- `git commit` always with -m. NEVER --no-verify (CLAUDE.md).
- Do not rebase, squash, amend, force-push, or touch already-pushed history.
  4b792c8, 04d15bb and 5be661e stay exactly as they are.
- Nothing is pushed. Nothing is merged. This is local history hygiene only.

VERIFY AT THE END
- `git status` clean (or only intentionally-untracked files, listed in your report).
- Full backend suite green on the final tree. RE-VERIFY the count yourself — recorded
  numbers have flapped between 208 and 215 and 218 across this multi-session work
  (D-022, and the shared-tree artefact noted in the 011 review). Report what YOU
  measure.
- `git log --oneline -8` pasted into your report.

STOP CONDITIONS — report, do not improvise:
- Any hunk you cannot confidently attribute to one task. Guessing wrong here silently
  splits a feature across two commits, which is worse than one blanket commit.
- Any test failing before you start. That is pre-existing and is not yours to fix in a
  git-surgery session — report it and stop.
- If `git add -p` cannot cleanly split a file because two tasks edited adjacent lines,
  say so and propose the smallest honest alternative (e.g. that file lands in one
  commit with a note in the message). Do not hand-edit files to force a clean split.
```
