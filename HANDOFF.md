# HANDOFF — AI Verkenner

> Volatile state. Overwritten at the end of every session; history lives in git.
> Read this FIRST at the start of every session (see CLAUDE.md session protocol).

## STATUS: GO — all four sessions ACCEPTED at the gate. Blocker is commit separation, not code.

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
6. **Task 016** — mention weight. Third occurrence of the same pattern (D-036, D-052, and the
   original 8-item cluster), so CLAUDE.md's three-use-case threshold is met (D-057).
7. **D-013** — orphaned-backlog defect, still open, still needs its own task file.

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
