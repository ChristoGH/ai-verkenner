# Decision log — AI Verkenner

> Append-only. Every significant discussion ends with an entry here: the
> context, the options weighed, the decision, and (once known) the outcome.
> Never rewrite an entry — a reversal is a NEW entry pointing back at the old
> one. This is how any future agent learns the *reasons* behind this repo.

Entry template:

```
## D-NNN · YYYY-MM-DD · <short title>
**Context.** Why this came up; what problem or discussion prompted it.
**Options.** What was considered, with the main trade-off of each.
**Decision.** What was chosen, and who decided (Christo / agent+review).
**Consequences.** What this commits us to; what it rules out.
**Outcome.** (fill in later) What actually happened; supersedes / superseded-by.
```

---

## D-001 · 2026-07-16 · Adopt the Tempo persistent-memory standard

**Context.** Chats and agent sessions leave no durable trace; future agents were not cognisant of the reasons, decisions and outcomes of prior discussions.
**Options.** (a) rely on chat history — not portable across agents/sessions; (b) ad-hoc notes in the vault — reasoning scattered away from the code; (c) per-repo standard: CLAUDE.md + HANDOFF.md + docs/memory/ + this log.
**Decision.** (c), installed and audited from kontekswerke-pomodoro (`scripts/memory/`). Christo, 2026-07-16.
**Consequences.** End-of-session protocol becomes binding: decisions are appended here, volatile state goes to HANDOFF.md, module maps stay diff-synced. The knowledge-vault holds cross-project reasoning; this log holds repo-local decisions.
**Outcome.** —

## D-002 · 2026-07-21 · Cause of the aborted M7.5 broad run: system restart, not sleep

**Context.** The STEP 3 broad run died mid-enrichment. The resume brief hypothesised system sleep, OOM, or terminal HUP, and asked for a diagnostic pass before re-running.
**Options.** (a) assume sleep and blindly rerun under `caffeinate -i`; (b) diagnose from system + corpus evidence first.
**Decision.** (b). Evidence: `pmset -g log` reports **Total Sleep/Wakes since boot: 0**; no `.panic` reports; no jetsam/`memorystatus` entries; no kill/abnormal-exit records in `log show`; Docker headroom ample (~2.2 GiB of 9.7 GiB). The corpus stops dead at `enriched_item.created_at` max **07:41:36**, and `kern.boottime` is **07:48:23** — the run was terminated by a **system restart** ~7 minutes after its last write. Agent (auto).
**Consequences.** Sleep, OOM and per-process kill are ruled out; `caffeinate -i` would not have prevented this. A restart can recur, so the rerun should stay resumable (enrichment is incremental — only NEW events are enriched, so a restart costs only in-flight work, not spend already made). Corpus state at halt: 199 events, 102 enriched (100 `llm`, 2 `fallback` dated 2026-06-22), **97 unenriched** — matching the brief's "~97".
**Outcome.** —

## D-003 · 2026-07-21 · Hold the billable broad run: convergence is red offline

**Context.** Pre-flight before spending on the remaining 97 events. Both suites were run for real counts: frontend **10 passed**; backend **163 passed, 5 failed, 1 skipped**. The only tracked diff vs `HEAD` (8d441fa) is `CLAUDE.md`, so the failures are **pre-existing in committed code**, not caused by the memory artifacts.
**Options.** (a) proceed with the run as authorised; (b) halt and escalate to Christo before spending.
**Decision.** (b) — halt, do not spend. Three of the five failures are the **convergence** computation returning 0/False (`test_dashboard_api` ×2 expect `convergence == 2` and get `0`; `test_posts_integration::test_posts_over_seeded_corpus` expects `has_convergence is True` and gets `False`). Cross-publisher convergence is precisely what the run exists to confirm (M7 Q2), so the run would exercise a provably broken path and its "no convergence" answer would be uninterpretable — broken code vs genuine corpus non-convergence. Agent (auto), pending Christo's review.
**Consequences.** This contradicts `docs/m7.5-broad-notes.md` ("complete and green offline", "all existing tests still green"); that verdict is now known stale and must not be trusted until the failures are resolved. Separately, `test_ingestion::test_orchestrator_isolates_a_broken_source` fails with `len(run.items) == 0` (expected 2) — a **direct violation of the CLAUDE.md invariant "Fail safely per source; one bad source must never break a run"**, which is acutely risky for a broad multi-source run. Steps 1–3 are not executed; no merge, push, or status flip made.
**Outcome.** —

## D-004 · 2026-07-21 · Reversal of D-003: no production bug — the 5 failures were fixture time-rot

**Context.** D-003 halted the billable run on the belief that convergence was broken and that the CLAUDE.md fail-safe invariant was breached. Root-cause analysis disproved both claims. This entry **supersedes D-003's diagnosis** (the halt itself was still correct — it was made on the evidence available).
**Options.** (a) widen `GRAPH_CONVERGENCE_WINDOW_DAYS` / `SOURCE_MAX_AGE_DAYS` in config to make tests pass — would change *production* behaviour to satisfy tests; (b) re-anchor the test fixtures to relative time.
**Decision.** (b). Root cause: fixtures used **hardcoded absolute dates** — `graph_helpers.TS`/`test_digest.TS` = 2026-06-18, `posts_fixtures._BASE` = 2026-06-15, and `tests/fixtures/rss_sample.xml` pubDates = 2026-06-16/17 — while both windows default to **30 days**. On 2026-07-21 the cutoff is 2026-06-21, so every fixture timestamp had aged *outside* the window. Proof: with `GRAPH_CONVERGENCE_WINDOW_DAYS=365 SOURCE_MAX_AGE_DAYS=365` the suite went **168 passed, 1 skipped, 0 failed** with no code change. These tests rotted on a calendar boundary (~2026-07-18), not on a commit. Agent (auto).
**Consequences.** **Convergence production code is correct** — D-003's "provably broken path" claim is withdrawn. **The fail-safe invariant is NOT breached**: `test_orchestrator_isolates_a_broken_source` showed `ok=True` for the good source and the failure correctly reported in `run.failed`; its items were merely filtered as too old. The `docs/m7.5-broad-notes.md` "green offline" verdict was accurate *when written*. The broad run is unblocked on this axis.
**Outcome.** Fixed in D-005; suite green on defaults.

## D-005 · 2026-07-21 · Re-anchor test fixtures to relative time

**Context.** Fixing the D-004 root cause without touching production windows.
**Options.** (a) bump the hardcoded dates — rots again in 30 days; (b) anchor fixtures to `datetime.now(timezone.utc) - timedelta(...)`; (c) inject a frozen clock throughout.
**Decision.** (b) — smallest change that removes the calendar dependency; (c) rejected as a larger refactor with no task file calling for it. Changes: `tests/graph_helpers.py` and `tests/test_digest.py` `TS` → `now - 3 days`; `tests/posts_fixtures.py` `_BASE` → `now - 7 days` (its `+1/+3/+5` day offsets stay in the past). `tests/test_ingestion.py` now passes `max_age_days=0` (orchestrator treats `0` as "window disabled", `orchestrator.py:44`) so the isolation test exercises isolation, not the recency cap. Agent (auto).
**Consequences.** Also fixed a latent bug in `posts_fixtures._item`: `_BASE.replace(day=_BASE.day + n)` raises `ValueError` when the offset crosses a month end — unreachable with a frozen 15 June base, reachable once `_BASE` moves. Now `_BASE + timedelta(days=n)`. **Test-only changes; no production code touched.** Suite on default settings: **168 passed, 1 skipped, 0 failed**; frontend **10 passed**.
**Outcome.** —

## D-006 · 2026-07-21 · Incident: broad run launched with the wrong CWD; ~15 enrichments billed to a stray DB

**Context.** The resumed STEP 3 run was launched as `cd backend && python -m app.cli run`, following the recipe in `docs/m7.5-broad-notes.md`. `settings.database_url` is **`sqlite:///./data/dev_corpus.db` — a relative path** — so with cwd=`backend/` it resolved to `backend/data/dev_corpus.db`, an empty file, instead of the real corpus at repo-root `data/dev_corpus.db`.
**Options.** (a) let the run finish and merge the stray DB; (b) kill immediately on detection.
**Decision.** (b) — killed as soon as the corpus showed 97 still-unenriched while the enricher was actively logging successes. Agent (auto). The run had re-ingested 175 events from scratch and performed **15 `llm` enrichments** (~$3–5) that duplicated work already paid for.
**Consequences.** **No data loss or corruption**: repo-root `data/dev_corpus.db` is untouched (199 events, 102 enriched, 97 unenriched). Wasted spend is bounded at 15 enrichments. A stray `backend/data/dev_corpus.db` now exists and should be deleted — pending Christo's confirmation, not removed unilaterally. **The runbook in `docs/m7.5-broad-notes.md` is wrong** and will re-trigger this for anyone who follows it: with a relative `DATABASE_URL` the CLI must run from the **repo root** (`PYTHONPATH=backend`), never from `backend/`. That doc needs fixing, but it is M7.5 status-adjacent so it is left for review.
**Outcome.** —

## D-007 · 2026-07-21 · Reversal of D-002: the restart did NOT kill the run (timezone error)

**Context.** D-002 concluded a **system restart** ended the first broad run, from "last enrichment 07:41:36, boot 07:48:23". That comparison was invalid.
**Options.** (a) let D-002 stand; (b) correct it once the unit mismatch surfaced.
**Decision.** (b). The machine is **UTC+2 (SAST)** and the corpus stores **naive UTC** (the documented M4 convention, `app/graph/util.py`). `enriched_item.created_at` max of `07:41:36` is **UTC = 09:41 local**; `kern.boottime` `07:48:23` is **local**. D-002 compared a UTC timestamp to a local one and inverted the ordering: the run was still writing **~2 hours after** the restart, so the restart cannot have killed it. Corroborated by `data/dev_corpus.db` mtime of 09:41 **local**. Agent (auto).
**Consequences.** **The cause of the first run's death is once again unknown.** It stopped at ~09:41 local, minutes before the prior session's artifacts stop (~09:48–09:49), which is consistent with **terminal HUP / session teardown** — Christo's original hypothesis, wrongly dismissed in D-002. The sleep and OOM findings in D-002 remain valid (0 sleep/wakes, no jetsam, no panic, ample Docker headroom); only the restart conclusion is withdrawn. Mitigation already applied: runs are launched detached via `nohup` + `caffeinate`, which survives session teardown. **Lesson: never compare a DB timestamp to a system timestamp without normalising the timezone first.**
**Outcome.** —

## D-008 · 2026-07-21 · Abort the resumed run on the first rule-based fallback, per instruction

**Context.** Christo's brief: "Abort on rule-based fallback, as before." Event 209 fell back with `no valid JSON object found in output`.
**Options.** (a) treat one malformed-JSON event as transient and continue — the LLM path was plainly healthy (107 `llm` successes); (b) honour the instruction literally and stop.
**Decision.** (b) — stopped immediately. Reinterpreting an explicit user gate without asking would be a silent decision, and aborting is nearly free here because **enrichment is incremental**: everything already paid for is retained and the run resumes where it left off. Agent (auto).
**Consequences.** Corpus at abort: **216 events, 110 enriched (107 `llm`, 3 `fallback`), 106 unenriched.** The unenriched count rose from 97 because ingestion added ~17 new events this run. Exactly **one** fallback occurred (event 209); the other two `fallback` rows date from 2026-06-22. This is a **per-event JSON parse failure, not systemic degradation** — materially different from the missing-API-key scenario the gate was written for. STEPS 2–3 (digest, posts) are **not** run, so the M7 Q2 convergence question remains unanswered. Needs Christo's ruling on whether isolated per-event fallbacks should abort or merely be logged.
**Outcome.** —
