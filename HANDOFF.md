# HANDOFF — AI Verkenner

> Volatile state. Overwritten at the end of every session; history lives in git.
> Read this FIRST at the start of every session (see CLAUDE.md session protocol).

## STATUS: GO — Task 010 Defect 1 reviewed and ACCEPTED; D-024 ruled (D-026). Task 013 is next.

<!-- GO = safe to start new work. NO-GO = fix the stated blocker first. -->

## Where things stand (2026-08-03)

Branch `feat/m7.5-broad-run`. **Task 010 Defect 1 (cluster coherence) is implemented, verified on
the real corpus, and uncommitted** — first code change since 2026-07-21. Do not self-merge
(CLAUDE.md review gate).

- **Tests**: backend **181 passed / 1 skipped / 0 failed** (baseline 174 + 7 new). Frontend
  untouched.
- **Corpus** (`data/dev_corpus.db`): 246 events, 246 enriched. **Last written 2026-07-21 — now 13
  days stale.** Unchanged this session (no fetch, no enrichment, no spend).
- **Graph**: populated and rebuilt from SQLite this session — 2130 nodes / 3666 rels / 246 Events.
  The task prompt's claim that `down -v` had emptied it was **false**; it was never empty (D-023).
- **M7.5 drafts: still HELD from publication** (D-016 A). The 8-item *incoherent* cluster is gone,
  but see the ruling request below.

### What changed (uncommitted)

`backend/app/digests/sections.py` · `backend/app/posts/generator.py` ·
`backend/app/scoring/graph_signals.py` · `backend/app/core/config.py` ·
`backend/tests/posts_fixtures.py` · **new** `backend/tests/test_cluster_coherence.py` ·
**new** `CHANGELOG.md` · `docs/DECISIONS.md` (D-019…D-025) · `docs/TECHNICAL_DESIGN.md` ·
`tasks/010-*.md`. Full detail in `CHANGELOG.md`.

A convergence is now claimed only when items share **one driving entity** (grouped on the entity
uid, not the display name); the cluster label is the entity, the "N independent sources" count is
scoped to that driver, the lead item's interpretation is attributed to that item, and an
`archive`-tier cluster discloses its tier on all three surfaces. `priority.py` untouched; no
threshold changed.

### Verification on the real corpus (LLM-free, $0)

`data/dev_corpus.db`, `--days 7`, window reproduced exactly as **2026-07-14 16:28 → 2026-07-21
10:45** (220 events, body 34 / noise 186). **The coherent-cluster path fired.** Regenerated drafts
are in `outputs/posts/` stamped `2026-08-03-*`, beside the original `2026-07-21-*` files for
comparison (`outputs/` is git-ignored). Regenerated LinkedIn hook:

> The AI signal most feeds will miss this week: OpenAI is quietly converging across 7 independent
> sources.

## THE ONE DECISION NEEDED FROM CHRISTO (D-024)

**The fix works; the output is still not publishable, for a reason Task 010 does not cover.**

Grouping by driver is correct and confirmed necessary — the quadrant's 84 converging items resolve
to **30 distinct drivers**, exactly the incoherence the review diagnosed. But group sizes are
hub-shaped:

| driver | items | | driver | items |
|---|---|---|---|---|
| OpenAI | 12 | | LLM | 5 |
| Large language models | 7 | | fine-tuning | 4 |
| Microsoft | 7 | | LLMs | 3 |
| Google | 7 | | Claude Code | 3 |
| AI | 6 | | *(13 singleton drivers)* | 1 |

"Largest group wins" therefore selects the **loudest** entity structurally, and M5.5's IDF
dampening does not prevent it (OpenAI spans 18 of ~246 developments → IDF ≈ 2.6, and its 7 distinct
sources dominate the product). Calling OpenAI "the AI signal most feeds will miss" is still an
overstatement — the same invariant Task 010 exists to protect.

I did **not** fix this: a driver-eligibility rule means changing convergence scoring, which this
task's non-goals forbid, and picking a non-largest group means substituting the specified rule.
Both would be silent scope changes.

**Recommendation:** authorise a Task 013 for **driver eligibility** — a hub/genericity gate on which
entities may *label* a cluster (not on which items converge). It should also cover the second defect
visible in that table: **"AI", "LLM", "LLMs", "Large language models" and "Artificial Intelligence"
are five entity uids for one concept** — entity normalisation, which both inflates driver counts and
fragments genuine clusters. Until then the weak-signal trio stays held.

## Next steps

1. ~~Review Task 010 Defect 1 and rule on D-024.~~ **DONE.** Defect 1 reviewed and accepted
   (grouping on `driver_uid` is correct); D-024 ruled by **D-026**. Commit the change set.
2. **Task 013** — driver eligibility. **This is the new blocker for any weak-signal publication.**
   D-026 ruled the selection objective is *quietest corroborated entity*, not *largest group* —
   "largest group" selected OpenAI and produced a self-refuting hook. Prompt in the task file.
3. **Task 010 Session 2** — Defects 2 + 3. Read **D-025 first**: the X hook truncation is caused by
   a 200-char lead URL, not the cluster label, so trimming prose alone will not close Defect 2.
   Independent of 013; can run in parallel.
4. **Task 014** — entity normalisation. **BLOCKED: 013 must merge first.** Normalising the five
   AI/LLM alias uids before the concept stoplist exists would create one *larger* hub and make the
   defect worse. The task file carries a precondition check.
5. **Task 011** — source scope + fetch health. Independent; can run in parallel.
6. **Task 012** — enrichment calibration. Independent; sample run only until Christo rules on the
   cost of full-corpus re-enrichment.
7. **Re-ingest to a current window — LAST, after 011 and 012.** The corpus is 13 days stale and the
   drafts cover 2026-07-14 → 07-21. Running it earlier re-ingests through three noisy
   whole-publication feeds and pays for enrichment under the prompt that produces collinear scores.
   Repo root, `PYTHONPATH=backend` (D-006). Also re-tests D-013.
8. **D-013** — orphaned-backlog defect, still open, still needs its own task file.

## Open questions / blockers

- ~~D-024~~ **RULED — see D-026.** The selection objective becomes *quietest corroborated entity*,
  not *largest group*. **Task 013 is now the blocker for weak-signal publication**, and Task 014
  (entity normalisation) is blocked behind it — normalising the five AI/LLM alias uids before the
  concept stoplist exists would build one *larger* hub.
- **Corpus staleness.** Any publication decision needs a fresh run first (step 5).
- **Eight enabled sources yield zero rows** (D-017) — Task 011.
- **`horizon_signal` empty — axis collinearity** (D-018, corrects D-014). `priority.py` is not the
  defect and stays untouched. Task 012. Note the whole 2026-07-21 cluster is `archive`-tier; the
  drafts now disclose that (D-016 ruling D).
- **The 174-passed baseline was date-dependent** and would have failed on the last days of any
  month — a latent fixture bug fixed this session (D-022). Treat recorded test baselines as
  re-verifiable, not as facts.
- **No `--now` / as-of flag on `app.cli digest|posts`** — any historical window is unreproducible
  from the CLI (D-023). Not fixed: unsanctioned scope. Worth a small task file.
- **Convergence image is still a placeholder** — `matplotlib`/`networkx` not installed.
- **Event 209 fell back twice** — persistently malformed item, not transient.
- **19 of 266 corpus items (7%) are off-topic**, all from three site-wide feeds (D-017).
