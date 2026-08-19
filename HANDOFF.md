# HANDOFF — AI Verkenner

> Volatile state. Overwritten at the end of every session; history lives in git.
> Read this FIRST at the start of every session (see CLAUDE.md session protocol).

## STATUS: GO — **Task 017 done and at the review gate** (2026-08-14); tasks 014, 015 (reverted) and 016 also at the gate on the four separation commits on `feat/m7.5-broad-run`. Suite with task 017: **247 passed / 1 skipped / 0 failed**, against a baseline re-verified today at `320ab8a` of **238 / 1 skipped** — re-run before citing. **One ruling is needed from Christo** (D-076, quadrant gate). See *Task 017* and *Commit separation* at the bottom; this line supersedes the earlier "five commits / 229 passed" claim.

<!-- GO = safe to start new work. NO-GO = fix the stated blocker first. -->

## ⚠️ Read this before trusting anything below (2026-08-04)

This HANDOFF was written by the **Task 010 Session 2** session (Defects 2 + 3). A **second session
was working in the same working tree at the same time**, on Task 013 and then Task 012. Its files
are present and uncommitted. **This session did not write, run, or review that work**, and reports
it only as observed:

- **Task 013 (driver eligibility)** — **complete and verified by that session; see its own section
  below** (added by the Task 013 session after this file was written). `sections.py`
  (`coherent_cluster` selection rule), `graph_signals.py` (`driver_mentions`), `config.py`
  (`WEAK_DRIVER_STOPLIST`), `tests/test_driver_eligibility.py`, CHANGELOG, TECHNICAL_DESIGN,
  `.env.example`, `docs/DECISIONS.md` **D-031…D-036** (renumbered around this session's D-028…D-030).
- **Tasks 011 / 012 (fetch health, enrichment calibration)** — **in flight** as this was written:
  `prompts/classify_item.md`, `enrichment/fallback.py`, `ingestion/orchestrator.py`,
  `ingestion/fetchers/github_intelligence.py`, `models/`, `sources/sources.yaml`, `.env.example`,
  `tests/test_classify_prompt.py`. Status unknown here — **ask that session, do not infer.**
- **`docs/DECISIONS.md` numbering — RESOLVED.** Both sessions briefly claimed D-028…D-030; the Task
  013 entries were shifted to **D-031…D-036** and this session kept **D-028…D-030**. No duplicates
  remain. See the numbering note in the file.

**Do not commit this tree as one change set without separating it.** Three tasks are interleaved.

## Where things stand — Task 010 Defects 2 + 3 (this session)

Branch `feat/m7.5-broad-run`. Presentation only: no scoring, no selection, no enrichment change.
`priority.py` untouched; no threshold moved.

- **Defect 2 (X character limit) — done.** `_fit_hook` became `_fit_x`: still the single trimming
  rule, now governing *every* emitted X post, with the evidence link as an **atomic** argument that
  is never trimmed. Sacrifice order: label → prose → label-to-nothing → hard cut. New `_thread()`
  numbers and fits every thread item so none escapes unchecked. New `_link_fits_in_hook()` moves the
  link out of the hook and into thread post 2 when it cannot sit there beside a readable label —
  which is what D-025 diagnosed. See **D-028**, **D-029**.
- **Defect 3 (Noise Report cap) — done.** New `NOISE_REPORT_LIMIT` (default **12**) caps what each
  surface *names*, loudest-first; `_noise_ranked()` returns the capped list **and the true demoted
  total**, and every surface states that total in prose. `is_noise` and the hype threshold untouched.
- **Files changed by this session:** `backend/app/posts/generator.py` ·
  `backend/app/core/config.py` (`noise_report_limit` only) · `backend/tests/posts_fixtures.py`
  (two new fixtures appended) · **new** `backend/tests/test_draft_surface_validity.py` ·
  `CHANGELOG.md` · `docs/DECISIONS.md` (D-028…D-030).

### Tests

Baseline **re-verified, not trusted** (D-022 / addendum §4): **181 passed / 1 skipped** on HEAD at
session start — matches the recorded number. Whole tree at the moment this was written (both
sessions' work interleaved): **204 passed / 1 skipped / 0 failed**. The five posts suites this
session owns are **39 passed, 0 failed**. That whole-tree number moves while the other session
works — **re-run before citing it.**

### Verification on the real corpus (LLM-free, $0)

`data/dev_corpus.db` via `build_digest_data(period_days=7, now=2026-07-21 10:45Z)` — the CLI still
has no as-of flag (D-023), so the window was reproduced by calling the builder directly. Graph was
already populated (2130 nodes / 3666 rels); no reindex, no fetch, no enrichment, no spend.
Window **2026-07-14 15:06 → 2026-07-21 10:45**: 221 events, body 34, **noise 187**.

| draft | 2026-07-21 (original) | 2026-08-03 (Defect 1) | now |
|---|---|---|---|
| noise-report-medium | 141,372 B | 140,674 B | **9,550 B** |
| noise-report-x | — | 15,951 B | 3,248 B |
| noise-report-linkedin | — | 16,095 B | 2,457 B |
| X posts over 280 chars | — | 9 | **0** |

Medium prose: *"187 items were demoted this week; these are the 12 loudest."* All source URLs
preserved on every weak-signal surface (0 missing). Drafts written to `outputs/posts/2026-08-04-*`
(git-ignored), stamped with today's date, not the window's (the rule D-035 arrived at). The whole
`outputs/` tree was deleted by the other session mid-run and these six files were restored from this
session's scratchpad copy — **`outputs/` is git-ignored and shared; treat anything in it as
destructible, and keep a copy outside it.**

Incidental observation, **not this session's work**: the weak-signal driver on that window is now
`Firefox` (2 items), not `OpenAI` (12) — the other session's Task 013 selection rule taking effect.

## Where things stand — Task 013, driver eligibility (added by the Task 013 session, 2026-08-04)

**Complete, verified on the real corpus, uncommitted — at the review gate. Do not self-merge.**
Selection only: convergence maths, IDF dampening, `GRAPH_MIN_SOURCES` and `graph_signals.py` scoring
are untouched, and `priority.py` was not opened (D-014).

- **Defect A (quietest wins) — done.** `coherent_cluster()` keeps membership on shared `driver_uid`
  and replaces the selection rule: among groups clearing `WEAK_CLUSTER_MIN_ITEMS` with a
  non-stoplisted driver, the **lowest ambient mention count** wins. Ties: lower mentions → larger
  group → higher summed `graph_score` → lower uid. The mention count is **threaded, not re-queried**
  — `ConvergenceStat.mentions` was already read and discarded (D-031, mirroring D-019's uid fix); the
  task's stop condition on adding a graph query was checked and did not fire.
- **Defect B (concept stoplist) — done.** `WEAK_DRIVER_STOPLIST` in `config.py`, seeded with 14
  terms commented by class, overridable via env. Matched on the normalised identity
  (`normalise_entity_name`). **Selection only** — nothing leaves the graph or scoring (D-033).
- **Audit trail:** the choice is logged at INFO from `sections.py`, so `app.cli posts` prints
  `weak signal driver: 'X' (uid=N) — mentions=…, distinct sources=…, group size=…` (D-034).
- **Files:** `backend/app/digests/sections.py` · `backend/app/scoring/graph_signals.py` ·
  `backend/app/core/config.py` (`weak_driver_stoplist` only) · `backend/tests/posts_fixtures.py`
  (one new `_item` kwarg) · **new** `backend/tests/test_driver_eligibility.py` · `CHANGELOG.md` ·
  `docs/TECHNICAL_DESIGN.md` · `.env.example` (WEAK_* block) · `docs/DECISIONS.md` (D-031…D-036) ·
  `tasks/013-driver-eligibility.md`.

### Verification on the real corpus (LLM-free, $0)

Same method and window as the sibling session: `build_digest_data(period_days=7, now=2026-07-21
10:45Z)` (D-023), graph already populated (2130 nodes / 3666 rels), no fetch, no enrichment, no
spend. **The coherent-cluster path fired.** Selected driver **`Firefox`** (uid 561) — **mentions 2,
distinct sources 2, group size 2**, the quietest of **12 eligible** groups out of **30** shared-driver
groups. `OpenAI` (17 mentions / 12 items) sorts last; `AI`, `LLM`, `LLMs`, `Large language models`,
`Artificial Intelligence` excluded as stoplisted. Hook:

> The AI signal most feeds will miss this week: Firefox is quietly converging across 2 independent
> sources.

Tier disclosure (archive) fires on all three surfaces; all source URLs preserved. Baseline
**re-verified on a clean HEAD worktree today: 181 passed / 1 skipped**; with task 013 alone the suite
was **187 / 1 skipped / 0 failed** (13 of those are the two weak-signal files and all pass in the
current tree).

### Incident and finding from that session

- **D-035 — the original `outputs/posts/2026-07-21-*` drafts were destroyed** by a verification run
  that stamped output with the *window* date instead of today's; `outputs/` is git-ignored, so there
  was nothing to restore. They were **reconstructed** from a `HEAD~1` worktree over the same corpus
  and are now `2026-07-21-reconstructed-*` (they reproduce the 8-item incoherent cluster exactly).
  The current `2026-08-04-*` set is this run's output. **Rule going forward: stamp regenerated drafts
  with today's date, never the window's.**
- **D-036 (finding, not fixed) — the `Firefox` cluster is quiet and coherent but only marginally an
  AI signal.** Its second item is a Mozilla release-cadence story from The Register's site-wide feed
  — one of the three whole-publication feeds D-017 measured. That reads as **corpus scope (Task
  011)**, not a selection defect. Also: three groups tie at mentions=2 / 2 items, so the
  `graph_score` tie-break decides among them — deterministic, but a thin margin.

### Task 013 Defect C — ATTEMPT 2, DONE (added 2026-08-04, at the review gate)

The Firefox finding above is **resolved**, by the route D-047 ruled: the floor, not the objective.

- **`WEAK_DRIVER_MIN_SOURCES`** (new, default **3**) and **`WEAK_CLUSTER_MIN_ITEMS`** raised
  **2 → 3**, both env-overridable and commented with why 3. One extra filter in
  `coherent_cluster()`; the tie-break chain is untouched; the audit log line now names the floor.
- **`GRAPH_MIN_SOURCES` stays at 2.** The new floor is selection-only.
  `test_graph_min_sources_unchanged` proves it rather than asserting a constant: a 2-source entity
  still returns a **positive** contribution from `graph_signals._contribution`, so a thin driver is
  still *convergent* — just not selectable as the face of the piece.
- **Files:** `backend/app/core/config.py` · `backend/app/digests/sections.py` · `.env.example` ·
  `backend/tests/test_driver_eligibility.py` (+3 tests) · `backend/tests/test_digest.py`,
  `test_posts_integration.py`, `test_cluster_coherence.py` (fixtures raised to the floor) ·
  `CHANGELOG.md` · `docs/DECISIONS.md` (D-051, D-052) · `tasks/013-driver-eligibility.md`.

**Verification** — same method and window (`build_digest_data(period_days=7, now=2026-07-21
10:45Z)`, D-023), graph already populated, no fetch, no spend. Winner **`Claude Code` — 5 mentions,
4 distinct sources, 3 items**, quietest of **5 eligible** groups of 30:

| driver | mentions | sources | items | |
|---|---|---|---|---|
| **Claude Code** | **5** | 4 | 3 | ← selected |
| fine-tuning | 6 | 4 | 4 | |
| Microsoft | 9 | 3 | 7 | |
| Google | 9 | 4 | 7 | |
| OpenAI | 17 | 7 | 12 | sorts last |

`Firefox` (2/2) excluded; `xAI` and `distribution shift` excluded on items; the AI/LLM concept family
still stoplisted. Hook: *"The AI signal most feeds will miss this week: Claude Code is quietly
converging across 4 independent sources."* Tier disclosure fires on all three surfaces; 0 missing
URLs. Drafts `outputs/posts/2026-08-04-*`.

**Suite: 218 passed / 1 skipped / 0 failed.** Nine tests failed on the raised floor because their
fixtures predated it; they were **raised to the new floor, not exempted** (D-051) — `_seed` now has
three converging developments across three sources. **No production threshold was lowered.**

**Residual finding (D-052), not fixed:** two of the three `Claude Code` items are substantively about
it; the third references it once, in passing. All three links are genuine — better than D-036's
Firefox item, which had no AI content at all — but *mention weight* is an unruled question, separate
from the floor and from corpus scope.

## Where things stand — Task 011, source scope + fetch health (added by the Task 011 session, 2026-08-04)

**Both defects complete, verified against live feeds, uncommitted — at the review gate. Do not
self-merge.** Enrichment, scoring, `priority.py` and `prompts/classify_item.md` were not opened.

- **Defect 1 (source scope) — done, applied verbatim.** `MIT Technology Review`, `The Register` and
  `Hacker News (front page)` replaced by their AI-topic feeds and renamed. All three replacement
  URLs fetched before committing: **50 / 10 / 20 entries**. No other registry entry touched; no
  corpus row deleted.
- **Defect 2 (fetch health) — done.** New `SourceHealth` table · new
  `backend/app/ingestion/health.py` · `SourceRunResult` gains fetched/new/skipped/needs_token ·
  `upsert_source_health()` called from `ingest_and_store` **after** commit · `python -m app.cli
  sources --health` · a loud, non-fatal zero-yield warning at the end of `run`. Reporting only —
  no retries, no backoff, no breaker, no auto-disable.
- **Files:** `sources/sources.yaml` · `backend/app/ingestion/orchestrator.py` · **new**
  `backend/app/ingestion/health.py` · `backend/app/ingestion/fetchers/github_intelligence.py` ·
  `backend/app/models/entities.py` + `__init__.py` · `backend/app/storage/repository.py` ·
  `backend/app/storage/pipeline.py` · `backend/app/cli.py` · `backend/app/core/config.py`
  (`source_zero_yield_warn` only) · **new** `backend/tests/test_source_health.py` · `.env.example` ·
  `CHANGELOG.md` · `docs/TECHNICAL_DESIGN.md` · `docs/m7.5-broad-notes.md` ·
  `docs/DECISIONS.md` (D-037…D-041) · `tasks/011-*.md`.
- **Tests:** the four named in the task file plus six more (10 total), all green. Full backend suite
  **214 passed / 1 skipped / 0 failed** — but that number covers all four sessions' work, not this
  one's. Re-run rather than trusting it (D-022, addendum §4).

### Verification against live feeds (no spend, corpus untouched)

Three real ingestion runs against a **scratch** SQLite file, with `qdrant_client=None`,
`enricher=None`, `graph_store=None` — no vector writes (the m75broad Qdrant index was left alone),
no Neo4j writes, no LLM calls. Run 2 hit a **live transient arXiv cs.CL failure**, it was isolated,
and the run completed: the fail-safe invariant demonstrated in the wild, not just in a fixture.
`sources --health` classified 26 enabled sources as 15 `ok` · 7 `no-token` · 4 `stale-window` ·
0 `no-items` · 0 `error`.

### Two findings that correct D-017 — these need a ruling

1. **The recency cap, not broken feeds, is the dominant cause of zero yield (D-041).** Effective
   `SOURCE_MAX_AGE_DAYS` here is **7**, direnv-injected — not the `30` that `config.py` documents
   and `.env.example` shows. Nothing in the repo records the override. **Consequence:** any source
   publishing monthly is structurally invisible, which biases the corpus toward high-frequency
   publishers — the same publishers Defect 1 just narrowed for being noisy. Raising the cap to 30
   restores four sources at the cost of a larger enrichment bill. **Tuning decision, escalated not
   taken.**
2. **D-017's "eight zero-yield sources" is wrong in both directions (D-037/D-041).** `Qdrant
   Releases` and `VentureBeat AI` also yield zero and were never named (11 flagged on the live
   probe, not 8). Conversely **LlamaIndex Releases** and **Eugene Yan** fetch perfectly — 30 and
   212 entries — and are merely quieter than a 7-day window. They are **left enabled** and report
   as `stale-window`; disabling a working source to satisfy the acceptance criterion is the
   manufacture-a-result failure the addendum §5 names. **The criterion "every one of the eight is
   fixed or disabled-with-reason" is therefore met in substance, not literally.** A strict reading
   is a two-line YAML change.

Resolved as specified: **LangChain Blog fixed** (feed moved to `www.langchain.com/blog/rss.xml`;
the old URL 302s to HTML — 200, zero entries, silently no rows). **Anthropic News disabled** (no
feed at any of seven probed paths; the status feed is incident history, a different source, so
substituting it was refused — D-038). **Neo4j Releases disabled** (GitHub Releases dead since
2017-09-15; the repo is tagged, not released). Anthropic — a frontier lab at `trust_level: high` —
is now **uncovered**, and that gap is real and deliberate rather than silent.

## Next steps

**Review gate cleared on all four sessions.** Task 010 (Defects 1,2,3) · Task 011 (D-050) ·
Task 012 (closed, D-057) · Task 013 (Defects A,B,C). Nothing is blocked on a ruling.

1. **Separate the tree into five commits — THE BLOCKER.** Four sessions wrote this tree
   concurrently; a blanket commit makes all four unbisectable. Plan and paste-ready prompt:
   [`docs/reviews/2026-08-04-commit-plan.md`](docs/reviews/2026-08-04-commit-plan.md).
   Nothing new starts until this is done.
2. **Task 014** — entity normalisation. Unblocked once 013 commits. Must come after 013 (D-026).
3. **Fresh ingest to a current window.** Now the highest-value step and the last thing between the
   project and publication: sources are fixed (011), the prompt is recalibrated (012), selection is
   sound (013). Corpus stops at 2026-07-21. Recipe in `docs/m7.5-broad-notes.md` — repo root,
   `PYTHONPATH=backend` (D-006). Also re-tests D-013.
4. **PUBLISH.** Christo only. The quality defects that held the drafts are all fixed.
5. **Task 015** — relevance anchors over-demote; `relevance` and `actionability` never reach 4,
   so `immediate_priority` is now as starved as `horizon_signal` was (D-057).
6. ~~**Task 016** — mention weight.~~ **DONE, at the review gate** — see the Task 016 section at the
   bottom of this file. One acceptance criterion (the D-036 Mozilla item) is **not met and cannot be
   met by mention weight**; it needs a ruling, not a fix (D-068).
7. **Topicality as its own task** — the half of D-036 that mention weight cannot answer: an item can
   be strongly about `Firefox` and not about AI. Recommended by D-068; **measure after the fresh
   ingest first**, since task 011 already replaced the feed both offending items came from.
8. **D-013** — orphaned-backlog defect, still open, still needs its own task file.

## Open questions / blockers

- **NEW (D-028) — should X drafts count links at their real length or X's t.co length (23)?** On the
  real corpus a 162-character URL leaves a FACT thread item ~30 characters of summary beside its
  link. That is the task file's stated preference ("keep the URL, truncate the prose") followed
  literally, and it yields near-contentless FACTs. Counting links at 23 characters is how X actually
  measures a post and would fix it outright — but it bakes an unversioned platform assumption into
  the budget and makes the acceptance criterion self-referential. **Not taken silently; needs a
  ruling.** Shortening source URLs is the other remedy.
- **M7.5 drafts remain HELD from publication** (D-016 A) until the weak-signal trio is reviewed.
- **Corpus staleness (14 days).** Any publication decision needs a fresh run first.
- ~~**Eight enabled sources yield zero rows** (D-017)~~ **— CLOSED by Task 011**, and the audit that
  raised it is corrected: the count was wrong (11, not 8) and two of its eight sources were never
  broken (D-037/D-041). Zero yield is now visible every run and classified by cause. **Two things
  replace it as open:** (a) `SOURCE_MAX_AGE_DAYS=7` vs the documented 30 — a tuning decision for
  Christo, see the Task 011 section; (b) **Anthropic is now an uncovered frontier lab** (no feed
  exists), which is a real gap in an early-warning system, now explicit rather than silent.
- **`horizon_signal` still empty — axis collinearity** (D-018). `priority.py` is not the defect.
  **Task 012 attempt 1 is done and did not fix it** — see the Task 012 section below and D-046; the
  prompt rewrite narrowed the gap instead of widening it, and the measured cause is that
  `strategic_potential`'s anchors are conditioned on the same thing `relevance` is. D-018's "6 items
  would become `horizon_signal`" is corrected to **0** by D-045. The 2026-07-21 cluster is still
  `archive`-tier; the drafts disclose that (D-016 D).
- **No `--now` / as-of flag on `app.cli digest|posts`** (D-023) — historical windows are only
  reproducible by calling `build_digest_data` directly, as this session did. Worth a task file.
- **Convergence image is still a placeholder** — `matplotlib`/`networkx` not installed.
- **Recorded test baselines are re-verifiable claims, not facts** (D-022, addendum §4).

---

## Task 012 — enrichment score calibration (session 4 of 4 in this tree, 2026-08-04)

**Written by the Task 012 session.** Appended, not overwritten, per D-042 — three other sessions'
state is above this line. **STOP CONDITION HIT: needs a ruling from Christo (D-046) before attempt 2.**

### What changed (uncommitted)

`prompts/classify_item.md` (rewritten) · `backend/app/enrichment/fallback.py` (comment mirror only,
scores untouched) · **new** `backend/tests/test_classify_prompt.py` (5 tests) · **new**
`backend/scripts/measure_calibration.py` · **new** `docs/m8-calibration-notes.md` ·
**new** `docs/m8-calibration.json` (raw run output) · `tasks/012-*.md` · `docs/DECISIONS.md`
(D-043…D-046).

All five of Task 012's scope points are implemented: the blanket downward tiebreaker on `relevance`
is gone (only `hype` keeps one), every axis carries 0–5 anchors with 4 and 5 defined, an explicit
"score `strategic_potential` first and independently" section states that `rel 0–1` + `sp 4–5` is a
correct answer, one worked low-relevance/high-strategic example is included, and the tiebreaker
wording is mirrored into `fallback.py` with a test pinning the mirror.
**`backend/app/scoring/priority.py` is untouched** (D-014 standing ruling). No axis renamed or
re-ranged; the hype inversion is unchanged.

### The measurement — it did not clear the bar

45 held-out corpus items re-scored under the new prompt, classify prompt only, corpus opened
read-only (nothing written back). Full detail in `docs/m8-calibration-notes.md`.

| Measure | Before | After | Target |
|---|---|---|---|
| `r(relevance, strategic_potential)` | 0.889 | **0.749** | < 0.5 ❌ |
| items at `rel ≤ 2 AND sp ≥ 4` | 0 | **0** | ≥ 1 ❌ |
| `relevance` reaches ≥ 4 | 1 | **0** | ≥ 1 ❌ |
| `actionability` reaches ≥ 4 | 0 | **0** | ≥ 1 ❌ |

**The gap distribution is the real finding**, not the correlation: mean `sp − rel` **fell** from
0.42 to 0.31, and **not one item in 45 reached `sp ≥ rel + 2`**. The rewrite made scoring slightly
more conservative on four of five axes rather than decoupling the two.

**Measured cause.** `strategic_potential`'s anchors are conditioned on the user's current stack — a
3 is "a credible alternative to something already in the stack", a 4 is a shift "in an area they
build in". That is what `relevance` measures. Items far from the stack score low on **both by
construction**, so "score them independently" asks the model to override a definition it was also
given. D-018 named the tiebreaker as *a* cause; this is the deeper one.

**Calibration did not become inflation** — the opposite. Four of five axis means fell. The hype
inversion was correct on every sampled item at both ends (sponsored Gartner content → 5; a primary
Simon Willison post → 0). The 10-item hand spot-check is in the notes, misses included.

**Cost: $1.42** (45 sample calls + 2 smoke calls; 156,501 in / 23,126 out tokens on
`claude-opus-4-8`). Full-corpus re-enrichment was **not** run and is not authorised.

### THE DECISION NEEDED FROM CHRISTO (D-046)

1. **Is re-framing `strategic_potential`'s frame of reference in scope for Task 012?** The fix that
   the evidence points at is defining it against *the shape of the problem the user works on*
   rather than *the contents of their current stack*. That rewrites one axis's anchors — more than
   "calibration", but it does not touch the axis names, ranges, the hype inversion, or `priority.py`.
   **Recommendation: yes, authorise it inside Task 012**, with event 54 (*Inkling*, open-weights
   975B under Apache-2.0 — currently scored `rel 2 / sp 3`, should be `rel 1–2 / sp 4–5`) as the
   regression fixture. A second sample run costs about $1.40.
2. **Should Task 011's source-scope fix land first?** Three site-wide feeds put genuinely off-topic
   items ("Viking 1 landed on Mars", a UK government ERP audit) into every sample. Measuring on a
   cleaner corpus would be cheaper and more honest. **Recommendation: yes, but it does not block —
   the sample also contains items that *should* land in the quadrant and did not.**

### Tests

`204 passed / 1 skipped / 0 failed` on the full backend suite (`PYTHONPATH=backend`,
`backend/.venv/bin/python -m pytest backend/tests`), re-run this session — that count includes the
other three sessions' new tests as well as this task's 5. Treat it as re-verifiable, not a fact
(D-022, addendum §4).

### Task 012 — ATTEMPT 2, DONE (added 2026-08-04 by the attempt-2 session, at the review gate)

**Scope point 6 only, authorised by D-049. Attempt 1's points 1–5 are untouched and stay.**
**STOP CONDITION HIT AGAIN — needs a ruling (D-056). Do not iterate a third time.**

`strategic_potential` is now scored against **the shape of the problem space** — agentic pipelines ·
retrieval and knowledge graphs · evaluation and traceability · trust-sensitive domains — instead of
the contents of the current stack. The two attempt-1 anchors that made it a restatement of
`relevance` ("a credible alternative to something already in the stack"; a shift "in an area they
build in") are gone, and `test_strategic_potential_is_framed_on_the_problem_space_not_the_stack`
asserts they cannot return. The scoring section states the axes read **different evidence**:
`relevance` reads `user_context`, `strategic_potential` explicitly does not. Mirrored into
`fallback.py` (comment + a note on why its flat `sp = 2` must not be derived from stack keywords);
scores unchanged there. `priority.py` untouched; no axis renamed or re-ranged.

**Files:** `prompts/classify_item.md` · `backend/app/enrichment/fallback.py` (comments only) ·
`backend/tests/test_classify_prompt.py` (+1 test, 6 total) · `docs/m8-calibration-notes.md`
(attempt-2 section appended; attempt 1 intact) · **new** `docs/m8-calibration-attempt2.json` ·
`CHANGELOG.md` · `tasks/012-*.md` · `docs/DECISIONS.md` (D-053…D-056).

| Measure | Before | Attempt 1 | **Attempt 2** | Target |
|---|---|---|---|---|
| `r(relevance, strategic_potential)` | 0.889 | 0.749 | **0.693** | < 0.5 ❌ |
| items at `rel ≤ 2 AND sp ≥ 4` | 0 | 0 | **2** | ≥ 1 ✅ |
| `horizon_signal` items | 0 | 0 | **2** | first time non-zero |
| items at `sp ≥ rel + 2` | 0 | 0 | **4** | — |
| `relevance` / `actionability` reach ≥ 4 | 1 / 0 | 0 / 0 | **0 / 0** | ≥ 1 ❌ |
| event 54 (*Inkling*) in the quadrant | — | no | **no (`rel 2 / sp 3`)** | yes ❌ |

Same 45 items as attempt 1 (verified element-by-element **before** spending), same seed, model and
`USER_CONTEXT`; corpus read-only, nothing written back. No inflation: relevance and novelty means
fell again, `sp`'s mean is flat at 1.73 while its distribution spread both ways, hype inversion
correct on every item, off-topic items did not drift up. **Cost $1.62 vs ~$1.40 approved** (+16%,
cause recorded in D-055); $3.04 across both attempts. Full-corpus re-enrichment still unauthorised
and not run.

**What the ruling (D-056) should weigh.** (1) Attempt 1's **`relevance` anchors now over-demote**
stack-adjacent items (`rel ≥ 4`: 1 → 0; events 1, 103, 228 each lost a point), so part of the
quadrant's reachability was bought there — fixing it would *raise* `r` while making both axes more
truthful. (2) On this sample **`r` may be the wrong instrument**: it is held up by the ~33 items that
genuinely belong on the diagonal (Mars anniversary, Gartner ad), while the measures that track the
product requirement — quadrant occupancy and the `sp − rel` gap — both moved. The criterion was
**not** changed to fit the result. (3) 4 of 45 items are headline-only stubs, including one of the
two quadrant items (event 180); Task 011 has landed, so a re-measure on a fuller corpus is the
cheapest next signal. Model variance is real: event 179 moved `sp 4 → 3` between runs on identical
input.

Suite after this work: **218 passed / 1 skipped / 0 failed** (whole tree, four sessions' work) —
re-run before citing.

---

## Task 011 — REVIEW GATE: ACCEPTED (reviewed 2026-08-04 by the Task 012 session)

**Task 011 is accepted (D-050).** Reviewed against ground truth — live fetches and a copy of the
corpus — not against the implementing session's report, since four sessions share this tree.

**Verified:** all four replacement/fixed feeds return well-formed on-topic content at the claimed
counts (Register — AI/ML 50 · MIT TR — AI 10 · HN AI/LLM ≥100 20 · LangChain 100); Defect-1 blocks
applied verbatim with no unauthorised registry edits; a live 26-source health run produced **zero
`no-items`** (the genuinely-broken state), `stale-window` on exactly the four sources D-041 named,
`no-token` on all seven `github_*` sources with their own reason, and 11 zero-yield warnings printed
**non-fatally after a successful run**. `test_source_health.py` 10/10 including all four named
tests; Task 011's blast radius 56/56; full suite **215 passed / 1 skipped / 0 failed**.

**Closed at the gate:** D-048's amended criterion wants every retained zero-yield source to have its
cadence recorded; only two of four did. Added cadence comments for `Qdrant Releases` (newest
v1.18.3, 2026-07-17) and `VentureBeat AI` — `sources/sources.yaml` only, no logic touched.

**⚠️ New finding — watch `VentureBeat AI`.** It parses cleanly but its newest item is **2026-05-19**,
2.5 months stale for a daily publisher. That looks like a stopped feed, not low cadence. Left
enabled with a dated watch-note; if it is still frozen at the next review, fix the URL or disable it.

**Still open, inherited not resolved:** `SOURCE_MAX_AGE_DAYS` is **7** in this environment vs **30**
documented (D-048 — Christo's tuning call; every window-dependent measurement in this repo silently
depends on it). Renaming a source orphans its `source_health` row, so the three renamed feeds start
their fetch history fresh.

**Note on suite counts in this tree:** the full-suite number flapped between 208 and 215 across
consecutive runs while other sessions edited files mid-run. That is a shared-tree artefact, not a
defect. 215 / 1 skipped / 0 failed is the settled number — re-run before citing it (D-022).

---

## Task 014 — entity normalisation (added 2026-08-04, at the review gate)

**Implemented, verified on the real corpus, uncommitted. Do not self-merge.**

**Precondition checked in code, not docs** (the task prompt requires it): Task 013 is merged at
`1873d78` — quietness selection, `WEAK_DRIVER_STOPLIST` and the defect-C floors are all present in
HEAD. Working tree was clean before this work began.

Alias surface forms now resolve to one canonical entity **at graph projection time**, from
`sources/entity_aliases.yaml` — a curated, human-readable file that is the complete record of every
merge. No fuzzy matching, no embeddings, no learned resolution; an unlisted form stays its own
entity. SQLite is never rewritten, so **deleting the YAML and re-running `graph-reindex` restores
the previous graph exactly** — that is the rollback path (ADR 0001).

- **Files:** **new** `backend/app/graph/aliases.py` · **new** `sources/entity_aliases.yaml` ·
  **new** `backend/tests/test_entity_aliases.py` · `backend/app/graph/projection.py` ·
  `backend/app/scoring/graph_signals.py` · `backend/app/core/config.py` (`entity_aliases_file`
  only) · `CHANGELOG.md` · `docs/TECHNICAL_DESIGN.md` · `docs/DECISIONS.md` (D-058…D-061) ·
  `tasks/014-entity-normalisation.md`.
- The canonical uid is a **real `Entity.id`**, and `graph_signals` resolves the event's SQLite ids
  through the same map — otherwise every aliased entity would silently lose its graph signal
  (D-058). `INTERACTS_WITH` self-loops created by a merge are dropped so normalisation cannot
  inflate the degree term (D-060).

### Measured on the real corpus (LLM-free, $0)

Window 2026-07-14 15:06 → 07-21 10:45. Before = the graph as built, read with resolution disabled;
after = `graph-reindex` with the map on (a free rebuild).

| | before | after |
|---|---|---|
| distinct Entity nodes | 793 | **788** |
| distinct drivers in the quadrant | 30 | **26** |
| largest group | 12 | **27** |
| weak-signal driver selected | `Claude Code` (3 items) | **unchanged** |

**The sequencing was load-bearing, and now there is a number for it.** The AI/LLM family merges
from a largest fragment of 7 items into a single **27-item** group — by far the largest in the
quadrant. Under the pre-013 "largest group wins" rule, this task would have produced the worst
possible weak signal. With 013 in place the merged node is stoplisted and selection does not move;
`test_canonical_concept_still_stoplisted` pins exactly that.

### Two findings (D-061)

- **The concept family is SIX rows, not the five D-024 recorded** — `Large Language Model`
  (singular, id 61) was missed: `AI` · `Large Language Model` · `Large language models` · `LLM` ·
  `LLMs` · `Artificial Intelligence`.
- **No vendor-spelling family is fragmented in this corpus.** `OpenAI` / `Open AI`,
  `DeepMind` / `Google DeepMind` and the rest each match zero or one row, so they sit in the map as
  precautions. Today the entire measured effect is on the category node: the false-negative fix is
  demonstrated (in tests, and by the AI family merging) but **not yet load-bearing on real output**.
  It becomes load-bearing on the next ingest, when publishers spell vendors differently again.

### Tests

`backend/tests/test_entity_aliases.py` — the five the task names, plus
`test_fragmented_cluster_merges_into_one_driver` (three vendor spellings becoming one 3-source
driver) and two degradation/matching guards. Suite **229 passed / 1 skipped / 0 failed**, against a
baseline **re-verified today in a clean worktree at `bac590c`: 218 passed / 1 skipped** — not the
recorded number (D-022, addendum §4).

---

## Task 015 — relevance/actionability anchors: RUN ONCE, REVERTED (2026-08-04)

**Criteria unmet and Task 012's gates lost, so the change was NOT shipped** (D-062). One sample run,
hard stop, no iteration. `prompts/classify_item.md` and `backend/app/enrichment/fallback.py` are
back at their **committed attempt-2 state** (`git status` clean on both); the three Task 015 tests
were removed with them. Nothing to review in code — the deliverable is the finding.

| Measure | Attempt 2 | Task 015 | Gate |
|---|---|---|---|
| `relevance ≥ 4` | 0 | **0** | ≥ 1 ❌ |
| `actionability ≥ 4` | 0 | **0** | ≥ 1 ❌ |
| quadrant occupancy | 2 | **0** | ≥ 1 ❌ **LOST** |
| `sp ≥ rel + 2` | 4 | **2** | ≥ 3 ❌ **LOST** |
| `r` *(diagnostic)* | 0.693 | 0.608 | — |

### ⚠️ THE FINDING — bigger than this task

**`USER_CONTEXT` is the binding constraint on `relevance`, not the anchors.** The rewritten anchors
worked as written and correctly returned "no" on all 45 items, because the `user_context` actually
sent to the model is the **309-character default in `config.py`**:

> "…Stack: Python, FastAPI, SQLite, Qdrant, Neo4j, React/TypeScript, local sentence-transformers
> embeddings, **and a cloud LLM**…"

It names no products. So *"Anthropic pauses token-based billing for its Claude Agent SDK"* scored
`relevance` **2** — Anthropic is not a named part of the stack — and a Vite release with a changelog
scored `actionability` **2**. Both correct under the anchor as written.

Meanwhile **`docs/USER_CONTEXT.md`** — which calls itself *"the ground truth AI Verkenner uses to
score `relevance`"*, names Qdrant/Neo4j/FastAPI/React/Cursor/Voyage/AKS, and lists **"Claude /
Anthropic model + Agent SDK releases"** under *strong relevance signals* — **is not wired into the
runtime.** `USER_CONTEXT` is unset, so `config.py` falls back to the short paragraph.

**Every `relevance` score this project has measured — including D-018's corpus baseline — was
computed against a stack description omitting the user's most important named dependencies.**
Task 012 attempt 1 flagged this in its §6 and it was not acted on.

### Recommended next move — config + measurement, not another prompt rewrite

Point `USER_CONTEXT` at `docs/USER_CONTEXT.md` and re-measure. Under that context the two headline
misses meet the attempted `4` anchors on their face, so the same prompt that produced zero 4s here
would be expected to produce several. The attempted anchor text is preserved verbatim in
`docs/m8-calibration-notes.md` § Task 015 §5 so it need not be re-derived. Any retry should also fix
the protection clause's asymmetry — its only illustration shows `strategic_potential` *low*, which
is the most likely cause of the gate loss (9 items down, max 4 → 3), though on one run that cannot
be cleanly separated from the ±1 model variance attempt 2 already documented.

**Also open:** event 54 (*Inkling*), the regression fixture D-049 named, has now scored `sp 3` in
**three consecutive runs**. Either the fixture is wrong or the 4/5 anchors do not reach the
capability-under-a-permissive-licence case — settle it before citing it as a target again.

**Cost:** $1.73 vs ~$1.60 approved, 8% over, recorded not absorbed (D-063). Running total on this
prompt file across three runs: **$4.77**. Suite green: **226 passed / 1 skipped / 0 failed**
(re-verify before citing — other sessions are writing to this tree).

---

## Task 016 — mention weight (added 2026-08-04 by the Task 016 session, at the review gate)

**Complete, verified on the real corpus, uncommitted. Do not self-merge.** Appended, not
overwritten, per D-042 — Task 014's and Task 015's sections are above this line and were not touched.
**One acceptance criterion is deliberately NOT met — D-068, below. That needs a ruling, not a fix.**

Membership only: convergence maths, `GRAPH_MIN_SOURCES`, IDF dampening, task 013's floors and
stoplist and `priority.py` (D-014) are all untouched, and nothing is deleted from the corpus or the
graph. Decisions **D-064…D-068** (highest before this session: D-063).

### What changed

- **`backend/app/scoring/mention_weight.py` (new)** — one entity–item link's weight from the item's
  own title and published body: `1.0` named in the title · `0.8` named repeatedly · `0.6` named in
  the lead · `0.2` named once, body-only · `0.0` never named. Whole-word, case-insensitive,
  separator-tolerant, markup stripped. **No LLM call, no embeddings, no re-enrichment.**
- **`backend/app/digests/sections.py`** — `DigestItem.driver_weight` / `driver_weight_why` /
  `coverage_sources`; `coherent_cluster()` admits members at `>= CLUSTER_MEMBER_MIN_WEIGHT` and
  logs every member's weight, every weight-excluded item and the post-weighting source list at INFO;
  new `cluster_sources()` is the single source of truth for the published source count.
- **`backend/app/posts/generator.py`** — `_publishers()` delegates to `cluster_sources()`.
- **`backend/app/core/config.py`** (`cluster_member_min_weight` only) · `.env.example` ·
  **new `backend/tests/test_mention_weight.py`** (12 tests) · `backend/tests/posts_fixtures.py`,
  `graph_helpers.py`, `test_cluster_coherence.py`, `test_driver_eligibility.py` (fixtures gain
  `coverage_sources` / a real body) · `CHANGELOG.md` · `docs/TECHNICAL_DESIGN.md` ·
  `docs/DECISIONS.md` (D-064…D-068) · `tasks/016-mention-weight.md`.

### Verification on the real corpus (LLM-free, $0)

`data/dev_corpus.db` via `build_digest_data(period_days=7, now=2026-07-21 10:45Z)` — no `--now` flag
exists (D-023). Graph already populated (2125 nodes / 3663 edges, **already re-indexed by the Task
014 session**); no fetch, no enrichment, no spend. Window 2026-07-14 15:06 → 07-21 10:45, 221 events.

| | before (HEAD `bac590c`) | after |
|---|---|---|
| weak-signal driver | `Claude Code` | **`fine-tuning`** (6 mentions, 3 items) |
| published "independent sources" | **4** | **3** |
| actual publishers behind those items | 2 | **3** |
| cluster items substantively about the driver | 1 of 3 | **3 of 3** |

Hook: *"The AI signal most feeds will miss this week: fine-tuning is quietly converging across 3
independent sources."* Per-item audit from the run: ev205 `1.00` (named in the title) · ev166 `0.80`
(3× in the body) · ev235 `0.80` (2× in the body). **30 of ~85** quadrant entity–item links fell below
the floor. **45 source URLs across 6 drafts, 0 missing.** No drafts were written to `outputs/` — it
is git-ignored and shared, and other sessions are live in this tree (the D-035 lesson).

**D-052 NextBSD — excluded, and verified still present, not assumed:** weight `0.20` (*named once,
body-only, at character 73 of 84*); corpus row + URL present, enrichment row present, **5 graph
relationships** present, still named in the Noise Report. The `Claude Code` group drops to **1**
item, falls under `WEAK_CLUSTER_MIN_ITEMS=3` and stops being selectable — the honest degradation the
stop condition calls a correct result. **No floor was lowered.** The graph convergence read is
unchanged at 788 entities.

Two things worth knowing beyond the acceptance criteria:

1. **The published "4 independent sources" was already wrong before weighting (D-066).** Those 4 are
   the *entity's* publishers across the whole 30-day graph window; the 3 items standing behind the
   claim came from **2** publishers. Corrected here because task 016 mandates the count be computed
   after weighting — but it is an independent defect. **The task 013 eligibility floor still reads
   the graph-wide number** (out of scope to change), so the two now measure different things and
   should be reconciled by a future task.
2. **D-052 also called event 45 (*grok-mermaid*) substantive; its own text disagrees** — one mention,
   body-only, at character 349 of 483. It is excluded too. The weight is measured, not judged.

### ⚠️ The criterion that is NOT met — needs a ruling (D-068)

**"The Mozilla release item (D-036) does not count toward `Firefox`" is not reachable by mention
weight.** Measured: that item names `Firefox` **in its own headline** and scores **1.00**, the top
band. What it lacks is AI content — a **topicality** question, which this task's non-goals forbid and
which D-036 itself diagnosed as corpus scope (task 011). Excluding it would mean smuggling in a
topicality gate under a mention-weight name, or tuning a threshold until one item falls off it —
`AGENT_ADDENDUM.md` §5's named failure. So it was reported, not worked around, and pinned by
`test_mozilla_item_is_substantive_and_mention_weight_will_not_exclude_it`.

**Nothing published depends on it:** the `Firefox` pair is 2 items / 2 sources and is already
excluded by task 013's floor (D-047). **Recommendation: open topicality as its own task** rather than
widening task 016 — the two filters answer different questions and a reader needs to know which one
dropped an item. Task 011 has already replaced The Register's site-wide feed (the source of *both*
D-036's and D-052's offending items) with its AI/ML feed, so a fresh ingest may make the question
moot; measure before building.

### Tests

Baseline **re-verified, not trusted** (D-022 / addendum §4): **218 passed / 1 skipped** on a clean
`git worktree` at HEAD `bac590c` today. Task 016 **in isolation** (HEAD + only this task's files, so
Task 014's concurrent work is excluded from the attribution): **230 passed / 1 skipped / 0 failed**
— exactly +12, this task's tests. The whole shared tree moves while other sessions work; **re-run
before citing it.**

`backend/tests/test_mention_weight.py` carries the five tests the task file names plus seven more.
Both real cases are pinned **by name and with their real corpus text**, and every weight in the tests
is computed by the shipped function rather than hand-set, so a regression in `mention_weight` fails
the tests instead of leaving them asserting a typed-in constant.

### Note on the shared tree

`git status` was clean at this session's start; by the end **Task 014 and Task 015 files were also
uncommitted in it**. `backend/app/core/config.py` holds one hunk from each of Task 014 and Task 016;
`backend/app/digests/sections.py`, `posts/generator.py` and `scoring/mention_weight.py` are wholly
this task's; `backend/app/scoring/graph_signals.py` and `backend/app/graph/projection.py` are wholly
Task 014's and were **not opened** here. **Task 014's alias normalisation is live in this tree and
in Neo4j** (the graph was already re-indexed), so combined-tree numbers differ from the isolated
ones above — the driver, the exclusions and the published count are the same either way; only the
shared-driver group count moves (20 combined vs 22 isolated). **Separate these before committing.**

---

## Commit separation — DONE, four commits (2026-08-14)

**Appended, not overwritten** (D-042): every prior session's section above this line is untouched.
This session did **separation only** — no code was fixed, refactored, reformatted or improved, and
nothing was moved between commits to make a suite green.

`bac590c` (19 modified + 8 untracked, three tasks interleaved) → four ordered commits:

| # | SHA | message | suite on that commit |
|---|---|---|---|
| — | `bac590c` | *(baseline, re-verified in a clean worktree)* | **218 / 1 skipped** |
| 1 | `f07f25d` | `feat(graph): entity normalisation — one concept, one uid (task 014)` | **226 / 1 skipped** |
| 2 | `ae3e3c0` | `docs(calibration): task 015 run, reverted — USER_CONTEXT is the binding constraint (D-062)` | **226 / 1 skipped** |
| 3 | `0bf57b6` | `feat(digests): mention weight — a passing reference is not participation (task 016)` | **238 / 1 skipped** |
| 4 | `320ab8a` | `docs: addendum §7 (verify experiment inputs), D-069, task 017` | **238 / 1 skipped** |

Every number above was **re-run this session** (D-022, addendum §4), each in its own detached
`git worktree` at that commit — not in place. In-place runs would have returned 238 four times,
because index-only staging never changes the working tree (D-071).

**No intermediate commit was RED.** Tasks 014 and 016 are genuinely independent: neither needs the
other's code to pass. Commit 2 is correctly flat at 226 — task 015 shipped no code, only its record.

### Reconciliation — nothing lost, nothing added

- `git diff bac590c..HEAD` over the **19 modified** files: **+964 −47**, byte-identical to the
  pre-separation diffstat.
- Plus **7 new files**, +2281 (`aliases.py` 158 · `mention_weight.py` 129 ·
  `test_entity_aliases.py` 206 · `test_mention_weight.py` 454 · `m8-calibration-task015.json` 1073 ·
  `entity_aliases.yaml` 77 · `017-wire-user-context.md` 184).
- `git diff HEAD` was **empty** at commit 4 — the tree matched HEAD exactly.

### Three numbers this corrects

The combined tree is **238 / 1 skipped**, not the **229** the old status line carried nor the
**230** the task 016 session measured for its work in isolation. Both earlier figures were taken
mid-flight while other sessions were writing to this shared tree; neither was wrong when written.
The **218** baseline at `bac590c` re-verified exactly as recorded.

### Left uncommitted, deliberately

- **`docs/inbox-digests/`** — 3 untracked files, 52 KB (`2026-08-05-inbox-scan.md`,
  `2026-08-10-inbox-scan.md`, `README.md`), email-scan output belonging to **no task file**. Not in
  `.gitignore`. **Christo's call:** repo content, or `.gitignore`. Untouched by this session.
- **`HANDOFF.md` + `docs/DECISIONS.md`** (this section, and D-070…D-072) — written after commit 4,
  so they belong to no authorised commit. Left for the review gate rather than amending a reported
  SHA or adding a fifth commit (D-072).

### Found and NOT fixed, as instructed

1. **`HANDOFF.md`'s own status line was false** — it claimed "commit separation DONE (five commits)"
   *before any separation had happened*, and cited a suite number from a tree that no longer existed.
   Corrected in place (that is this session's own state to keep true, addendum §6), and the
   correction is stated rather than silently applied.
2. **`git status` was clean of task 015 code** — `prompts/classify_item.md` and
   `backend/app/enrichment/fallback.py` both unmodified, confirming D-062's revert really happened.
   The stop condition on finding live 015 anchors **did not fire**.
3. **`backend/app/scoring/priority.py` is absent from the whole diff.** D-014 intact.
4. **One assignment worth naming: `HANDOFF.md` carries task 014, 015 and 016 sections** but was
   committed whole in commit 4. By content those three sections belong to commits 1, 2 and 3. The
   plan assigned the file whole and this session followed it — defensible, since HANDOFF is volatile
   session state rather than a task deliverable, but it does mean **commits 1–3 do not carry their
   own HANDOFF narrative**. Flagged, not changed.

### Next steps (unchanged by this session, re-stated)

The separation blocker in *Next steps* above is now **cleared**. In the order that section sets:
**Task 017** (wire `USER_CONTEXT`) must land **before** the fresh ingest (D-069), then the fresh
ingest, then the publication decision. Task 015 should be re-read against Task 017's result before
anything is re-run.

---

## Task 017 — wire `docs/USER_CONTEXT.md` into the runtime (2026-08-14, at the review gate)

**Appended, not overwritten** (D-042). Every section above is untouched. **Do not self-merge.**
Decisions **D-073…D-077** (highest before this session: **D-072**, not the D-069 the task prompt
cited — D-070…D-072 were written by the separation session and are uncommitted).

### The wiring — done and proven at runtime, not just in tests

`USER_CONTEXT_PATH` (default `docs/USER_CONTEXT.md`) resolved through the **same** `_resolve()`
mechanism as `PROMPTS_DIR` / `SOURCES_FILE` / `ENTITY_ALIASES_FILE`. **No second path convention**
— pinned by `test_user_context_path_uses_existing_base_path_convention`. Precedence: explicit
`USER_CONTEXT` env → the file → the literal default.

**Proof, not assertion:** `python -m app.cli sources --health` prints
`INFO app.core.config: user_context source in force: …/docs/USER_CONTEXT.md (2331 chars)`, and the
calibration run's own JSON records the 2,331-character context it sent.

**No fall-back is silent (D-073).** An unreadable/empty configured file logs a **WARNING at
resolution time** — WARNING because `app.cli` imports settings at module level (`cli.py:29`) but
calls `basicConfig` inside `main()` (`cli.py:274`), so an INFO record emitted from `Settings.__init__`
is **discarded**. Announcing from `Settings` would have been a log statement in the diff and nothing
in the output. The steady-state line is emitted from the entry points instead.

- **Files:** `backend/app/core/config.py` · `backend/app/cli.py` · `backend/app/main.py` ·
  `.env.example` · **new** `backend/tests/test_user_context.py` (9 tests) · **new**
  `docs/m8-calibration-task017.json` · `docs/m8-calibration-notes.md` (appended) · `CHANGELOG.md` ·
  `docs/TECHNICAL_DESIGN.md` · `tasks/017-wire-user-context.md` · `docs/DECISIONS.md`.
- **Untouched:** `prompts/classify_item.md` and `enrichment/fallback.py` byte-identical to Task 012
  attempt 2 (verified clean before spending) · `priority.py` (D-014) · `docs/USER_CONTEXT.md`
  content · no new axes, no renaming, no hype-inversion change · **no full-corpus re-enrichment**.

### Scope item 3 discharged by measurement — nothing to trim

`docs/USER_CONTEXT.md` is **41 lines / 2,373 bytes / 2,332 characters** (byte-char gap = multi-byte
`—`/`·`); 2,331 after `.strip()`. **No trim boundary is proposed.** There is nothing to cut.

### ⚠️ A THIRD consumer the task prompt did not name (D-074)

`settings.user_context` is read by the enricher **and** the digest **composition** call **and** —
unnamed anywhere until now — `digests/retrieve.py:57` `build_theme_text`, which **embeds** it as the
Qdrant theme query selecting the digest's candidate pool. So wiring changes **which items a digest
retrieves**, not only how they are scored or described. Unmeasured; nothing in the acceptance
criteria depends on it. **Do not compare a post-017 digest with a pre-017 digest without re-measuring.**

### The measurement — one run, $1.81 of a ~$2.00 gate, not iterated

Same 45 items as all three prior runs, **identity verified element-by-element before spending**.
Prompts constant. 0 failed items.

| Measure | Attempt 2 | **Task 017** | Gate | |
|---|---|---|---|---|
| `relevance >= 4` | 0 | **1** | >= 1 | ✅ **MET** |
| quadrant (`rel<=2 & sp>=4`) | 2 | **0** | >= 1 | ❌ **LOST** |
| `sp >= rel + 2` | 4 | **3** | >= 3 | ✅ at the line |
| `actionability >= 4` | 0 | **0** | informational | — |
| `r(rel, sp)` *(diagnostic, D-057)* | 0.693 | **0.567** | not gated | fell (not predicted) |

**The prediction held.** ev1 — *Anthropic "pauses" token-based billing for its Claude Agent SDK* —
`rel 2 → 4`: the only item in the sample to reach 4, and **exactly the item named before the run**,
because `USER_CONTEXT.md` lists *"Claude / Anthropic model + Agent SDK releases"* verbatim as a
strong signal. ev38 (Claude) `2 → 3`. **D-062 is confirmed: the anchors were never the constraint,
and Task 015's premise is dead.**

**Caveat, measured before the run:** only **2 of 45** items match the predicted categories at all —
**zero** pgvector/Qdrant, **zero** tree-sitter, **zero** Knative. Three of the prediction's four
limbs were **untestable on this sample**. That is a fact about the sample, not a result.

**No inflation:** relevance mean **+0.02** (6 up, 6 down, 33 unchanged — redistribution, not lift);
hype inversion verified unchanged (Gartner 5, Willison 1). Cost **+931 input tokens/call,
+$0.0042/item (+11.5%), +$0.42 per 100 items**; four-run total on this prompt file **$6.58**.

### ⚠️ THE ONE THING THAT NEEDS A RULING (D-076)

**The quadrant did not empty because `relevance` rose. It emptied because `strategic_potential`'s
ceiling fell 4 → 3 — no item in 45 reached `sp >= 4`.** ev180 held `rel 2` *exactly* and lost
`sp 4 → 3`; ev38 likewise. `sp`'s **mean barely moved** (1.733 → 1.711); only the ceiling did.

That axis, by design, **does not read `user_context`** — Task 012 attempt 2 re-framed it on the
problem space precisely so it would not restate `relevance`, and a test pins that. Two readings:
**(1) variance** — the `sp >= 4` population was **2 of 45**, and D-056 already recorded ev179 moving
`sp 4 → 3` between runs *on identical input*; **(2) contamination** — a longer context implicitly
anchoring a pass on an axis meant to ignore it. **One run cannot separate them and the stop
condition forbade a second.** Nothing was tuned to recover the gate.

**Recommendation:** if this is worth settling, the cheapest instrument is a **repeat of this exact
run with nothing changed (~$1.81)**, which measures variance directly. A further *prompt* change
would confound the two again — the precise mistake this whole sequence exists to avoid. There is
also a real possibility the gate is simply **under-powered**: a criterion whose satisfying population
is 2 items wide on a 45-item sample may not be a stable gate at all. **Christo's call.**

### Two gaps in `docs/USER_CONTEXT.md` itself — reported, NOT edited (D-077)

Its accuracy is Christo's; the file says so. Found by the hand spot-check:

1. **Local LLM inference is absent.** ev179 (*Nativ: run frontier open models locally on your Mac*)
   fell `rel 3 → 2`. The document names embeddings but never local model *inference*, so the
   demotion is faithful to an under-specified text.
2. **"healthcare compliance" pulls non-AI healthcare items.** ev17 (*health board phishing
   exercise*) rose `rel 0 → 1` — a control item predicted not to move. Bottom-of-scale; nothing
   published depends on it.
3. **Not a document gap, and the most interesting miss:** ev228 (*memloom — local-first memory
   engine for AI agents*, from `topic:rag`) fell `rel 3 → 2` although "RAG techniques" is a named
   strong signal. The document covers it; the model did not act on it. This is the movement neither
   the wiring nor the document explains, and the best argument for taking D-076's variance
   hypothesis seriously.

If Christo edits the document, do it **before** any re-measure and as a **single-variable** change.

### Next steps — changed by this task

1. **Ruling on D-076** (quadrant gate) — the only thing blocked on Christo.
2. **Task 015 is superseded in premise.** Do not run it as written (D-062 already said so); its
   anchors were never the constraint. Re-read it against this result before touching it.
3. **The fresh ingest is now unblocked** — D-069's sequencing ("Task 017 must land BEFORE the fresh
   ingest") is satisfied, so new items will be scored against the real context rather than a stub.
4. Still open and untouched by this session: `SOURCE_MAX_AGE_DAYS` 7-vs-30 (D-048), Anthropic as an
   uncovered frontier lab, topicality as its own task (D-068), D-013 orphaned backlog, no `--now`
   flag (D-023), `docs/inbox-digests/` still untracked and unruled.

### Uncommitted, for the gate

Everything above is **uncommitted**, alongside the separation session's `HANDOFF.md` /
`docs/DECISIONS.md` update (D-070…D-072) which was also left for review. `docs/inbox-digests/`
remains untracked.
