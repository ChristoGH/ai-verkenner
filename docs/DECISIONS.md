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

## D-009 · 2026-07-21 · Redefine the fallback gate: systemic-only abort + retry-once

**Context.** D-008 aborted the resumed run on a single per-event fallback (event 209, malformed JSON) out of 107 healthy `llm` enrichments. That gate was written for the missing-API-key case, where *every* event degrades; it misfired on a transient parse failure. (Christo's instruction said "record as D-008", but D-008 was already taken by the original abort — renumbered to D-009 to keep the log append-only.)
**Options.** (a) keep the literal one-strike gate — stops a healthy run on noise; (b) systemic-only abort with a bounded retry.
**Decision.** (b), per Christo. New rule: **abort only on systemic degradation — ≥3 consecutive fallbacks, or a >10% rolling fallback rate.** Isolated per-event parse failures are retried once, then logged and passed over. Christo, 2026-07-21.
**Consequences.** `backend/app/enrichment/enricher.py` now retries `_llm_enrich` **once** before degrading; only a second consecutive failure for the same item yields `method="fallback"`. This is a **production code change with no task file calling for it** — flagged as a contract tension, made on Christo's explicit instruction. Two tests added (`test_transient_llm_failure_is_retried_once_and_stays_llm`, `test_persistent_llm_failure_falls_back_after_one_retry`); suite now **170 passed, 1 skipped, 0 failed**. The ≥3-consecutive / >10% thresholds are enforced **operationally by the run monitor**, not in production code — no task file sanctions an in-pipeline circuit breaker, and the cheap incremental resume makes an external gate sufficient. Event 209's fallback row was deleted so it re-enriches under the new rule; corpus went 110 → 109 enriched, 107 unenriched.
**Outcome.** —

## D-010 · 2026-07-21 · Delete the D-006 stray database

**Context.** `backend/data/dev_corpus.db` was created by the wrong-CWD incident (D-006).
**Options.** (a) leave it — a live trap for the next relative-path run; (b) delete after positive identification.
**Decision.** (b), per Christo, with identity verified before `rm`: 175 events and **all 15 enrichments created 08:47–08:52 UTC** (the D-006 window), and untracked by git — versus the real corpus at 216 events with history back to 2026-06-22. Christo, 2026-07-21.
**Consequences.** Deleted; `data/dev_corpus.db` verified intact at 216 events afterwards. `backend/data/ai_verkenner.db` (2026-06-22, the old default-path DB) was **left alone** — out of scope for this instruction.
**Outcome.** Done.

## D-011 · 2026-07-21 · Repair the malformed global settings.json

**Context.** `~/.claude/settings.json` was invalid JSON: the object had been duplicated onto itself (a valid prefix, a second complete copy, then a trailing fragment), so the whole file failed to parse.
**Options.** (a) hand-merge; (b) collapse to one object — both copies held identical values, so nothing was lost.
**Decision.** (b), per Christo, plus `"cleanupPeriodDays": 3650`. Backup taken first at `~/.claude/settings.json.bak-20260721-111836`. Christo, 2026-07-21.
**Consequences.** Validated with `jq`; all five original keys preserved (`model`, `enabledPlugins`, `extraKnownMarketplaces`, `effortLevel`, `agentPushNotifEnabled`) plus the new retention key. Outside this repo, so nothing committed.
**Outcome.** Done.

## D-012 · 2026-07-21 · Add `enrich --backfill` to drain orphaned Events

**Context.** `app.cli run` enriched only 2 events on a 220-event corpus with 107 unenriched. `enrich_new_events(session, enricher, new_rows)` (`enricher.py:184-196`) derives its work list from the rows persisted **by that run**, so Events stranded by an interrupted run are unreachable by any later `run`. The brief's "app.cli run — remaining ~97 events" was therefore not achievable as written.
**Options.** (a) new `enrich --backfill` subcommand; (b) a throwaway script; (c) author a task file first.
**Decision.** (a), per Christo. Selects Events with no `EnrichedItem`, enriches via the existing `Enricher.enrich_event` — no new enrichment logic. Supports `--limit` (cost control) and `--dry-run`. Deliberately does **not** fetch, dedup, or project; it prints the `graph-reindex` follow-up so the newly enriched Events reach Neo4j and count towards convergence, reusing the sanctioned rebuild path rather than duplicating projection. Christo, 2026-07-21.
**Consequences.** Production surface added with no task file — the same contract tension as D-009, on explicit instruction. Per-event isolation honours the fail-safe invariant: one failing Event is logged and skipped, never ending the backfill. 4 tests added (`tests/test_cli_enrich.py`), suite **174 passed, 1 skipped, 0 failed**. Dry run confirms 107 candidates.
**Outcome.** —

## D-013 · 2026-07-21 · Known defect: an interrupted run permanently orphans its unenriched Events

**Context.** Root cause behind D-012. `ingest_and_store` persists items first, then enriches them; if the process dies mid-enrichment, everything past the interruption point is committed-but-unenriched, and the next run's work list contains only *its own* new rows — so the orphans are never revisited. This is exactly how ~97 Events became stranded.
**Options.** (a) fix now by making the run's enrichment step sweep all unenriched Events; (b) log it and fix later under its own task file.
**Decision.** (b), per Christo — (a) is a behavioural change to the core loop and belongs behind a task file. Christo, 2026-07-21.
**Consequences.** `enrich --backfill` is the manual remedy; the defect itself remains and **will recur on every interruption**. Recorded in HANDOFF.md next-steps so it is not lost. Not a data-loss bug — the Events and their source URLs are intact, merely unenriched.
**Outcome.** —

## D-014 · 2026-07-21 · Observation (not a change): the horizon quadrant is empty by one relevance point

**Context.** After the full backfill (218/218 enriched), the priority distribution was `archive` 192 / `operational_update` 26 / **`horizon_signal` 0**. Weak Signal of the Week is drawn from the horizon quadrant, so an empty quadrant means no weak signal can be surfaced — despite genuine convergence existing in the graph.
**Options.** (a) relax the thresholds to force a signal; (b) record as a calibration observation and leave the rule alone.
**Decision.** (b), per Christo — **`backend/app/scoring/priority.py` stays untouched.** This is logged as an M8 calibration observation, not a change. Christo, 2026-07-21.
**Consequences.** Mechanism: `horizon_signal` requires **relevance ≤ 2 AND strategic_potential ≥ 4** (`priority.py:39-40`). Exactly **6 items reach `strategic_potential = 4`, and all 6 also carry `relevance = 3`**, so the preceding `relevance >= 3 → operational_update` branch claims them first. **Corpus max relevance is 3** and max strategic_potential is 4, so nothing reaches `immediate_priority` either. The quadrant misses by a single relevance point on six items — this reads as *enrichment score calibration*, not a defect in the priority rule (the rule is doing exactly what it says). Standing ruling: **if the quadrant is still empty after the `github_*` ingest, the digest ships with an honest empty weak-signal section plus the Noise Report; no threshold is relaxed to manufacture a signal.**
**Outcome.** —

## D-015 · 2026-07-21 · Corpus-level convergence (M7 Q2) confirmed on real feeds

**Context.** M7 Q2 asked whether cross-publisher convergence fires on a *real* corpus, not just the synthetic fixture. Answerable directly from the graph after `graph-reindex` over 218 enriched Events — no extra spend.
**Options.** (a) infer it from the digest output only; (b) query the convergence read directly as well.
**Decision.** (b) — read `Neo4jGraphStore.convergence(since)` over the configured 30-day window. Agent (auto).
**Consequences.** **Convergence fires: 107 entities span ≥2 distinct sources and 31 span ≥3**, out of 717 entities. Leaders: OpenAI (7 sources / 18 mentions / degree 23), Anthropic (6 / 9 / 11), Google (4 / 9 / 10), Microsoft (3 / 11 / 11). This answers M7 Q2 **yes at corpus level**, independently of whether the digest surfaces a Weak Signal of the Week — which is separately blocked by the empty horizon quadrant (D-014). The two facts must be reported together, or an empty weak-signal section would be misread as "convergence did not fire".
**Outcome.** —

## D-016 · 2026-08-03 · M7.5 review gate — draft outcomes

**Context.** The 2026-07-21 drafts were reviewed on 2026-07-25 (`docs/reviews/2026-07-25-m7.5-draft-review.md`). The weak-signal piece makes a false converging claim — 8 items, 1 of which supports the stated thesis — which fails Task 009's own acceptance criterion *"no false 'converging' claim"*. Root cause: `digests/sections.py:206-208` filters on the **per-item** property `it.convergence > 0`, collecting items that each converge on a **different** entity. `GraphSignal.driver` already names the driving entity per item and is never used for grouping.
**Options.** (A) hold the weak-signal trio; (B) require a shared `driver` for cluster membership; (C) honest degradation when no coherent cluster survives; (D) whether an `archive`-sourced weak signal is acceptable at all under D-014's spirit; (E) Noise Report top-N cap value; (F) publish a trimmed Noise Report standalone.
**Decision.** (A) hold the weak-signal trio — **yes**. (B) require a shared `driver` for cluster membership — **yes**. (C) honest degradation when no coherent cluster survives — **yes**. **(D) an `archive`-sourced weak signal is PERMITTED, provided the draft states the tier honestly and makes no claim of top-tier provenance.** D-014's ruling forbids relaxing a threshold to manufacture a signal; it does not forbid surfacing genuinely low-relevance items, which is precisely what a weak signal is. D-018 shows the quadrant is empty because of enrichment collinearity, not because nothing qualifies — that is fixed under task 012, not by withholding publication. (E) Noise Report cap = **12**. (F) a trimmed Noise Report **may** ship standalone. Christo, 2026-08-03.
**Consequences.** Task 010 (`tasks/010-convergence-cluster-coherence.md`) is **unblocked** and may start. Ruling (D) adds a requirement to Task 010 Defect 1: when the cluster is drawn from `archive`-tier items, the draft must **say so** — the honesty condition is part of acceptance, not a nicety. Note (D)'s precise mechanics: `horizon_signal` is 0, so the quadrant is non-empty only because `HORIZON_CLASSES = ("horizon_signal", "archive")` admits `archive`. No threshold was relaxed in code, so D-014's ruling was never broken literally; this entry settles the question of spirit. Revisit (D) once Task 012 lands and `horizon_signal` is genuinely populated — if the quadrant fills, the archive fallback should narrow or go.
**Outcome.** Ruled 2026-08-03. Task 010 clear to start; the tier-disclosure requirement flows into its Defect 1 acceptance criteria.

## D-017 · 2026-08-03 · Observation: three whole-publication feeds are diluting the corpus

**Context.** An MIT Technology Review opinion piece about **perimenopause** reached a published artifact (the Noise Report). Previously logged as a vague "source-registry relevance question". Audited empirically against `sources.yaml` + `data/dev_corpus.db`.
**Options.** (a) leave as an observation; (b) record the audit with exact remedial edits so the fix is a mechanical change.
**Decision.** (b). Agent (auto) — analysis only, no file changed.
**Consequences.** **19 of 266 raw items (7%) are plainly off-topic, and every one traces to one of three site-wide feeds**: The Register (`/headlines.atom`), MIT Technology Review (`/feed/`), Hacker News (`hnrss.org/frontpage`). Zero off-topic items came from a topic-filtered feed. Dilution is wider than the 7%: only 22% of Register, 33% of HN and 63% of MIT TR titles mention any AI/compute term, versus 69% for the scoped Ars `/ai/` feed. Exact YAML replacements are in `tasks/011-source-scope-and-fetch-health.md`. **Second, unrelated finding: eight enabled sources contributed 0 rows** — Anthropic News (its `url` points at an HTML page, not a feed), LangChain Blog, LlamaIndex Releases, Neo4j Releases, Eugene Yan, plus `github_star_velocity` / `github_advisories` / `github_changes`. Silent fetch failure with no surfaced error is a **fail-safe-isolation gap**: the invariant says keep going on a bad source, but a source that *never* yields must not stay invisible.
**Outcome.** —

## D-018 · 2026-08-03 · Correction to D-014: the empty horizon quadrant is axis collinearity, not top-of-scale compression

**Context.** D-014 recorded `horizon_signal = 0` and attributed it to score compression, stating max relevance 3 and 6 items at `strategic_potential = 4`. Re-measured directly against the 246-item corpus.
**Options.** (a) leave D-014 as written; (b) append a correction with the measured distributions.
**Decision.** (b) — the log is append-only, so D-014 stands and this corrects it. Agent (auto) — analysis only, `priority.py` untouched per the standing ruling.
**Consequences.** **Two factual corrections to D-014:** max relevance is **4, not 3** (one item, rel=4 & sp=4 — the sole `immediate_priority`), and **7** items reach sp=4, not 6. **The real mechanism is collinearity, not compression:** r(relevance, strategic_potential) = **0.842**, and `strategic_potential` never exceeds `relevance + 1` except for **one item in 246**. Since `horizon_signal` requires `sp >= relevance + 2`, the quadrant is **structurally unreachable** regardless of where the thresholds sit — the priority rule is behaving exactly as written and is not the defect. Likely cause is in `prompts/classify_item.md:56-58`: *"when unsure, prefer the lower end of relevance and the higher end of hype"* — a blanket downward tiebreaker on relevance (mean relevance 1.2), with nothing anywhere instructing the model to **decouple** `strategic_potential` from `relevance`, and no anchors defining what a 4 or 5 looks like on any axis. Same text mirrored in `backend/app/enrichment/fallback.py:25`. Fix magnitude: 6 items would become `horizon_signal` immediately; a further 23 sit at sp=3 & rel<=2. Remediation is prompt-only — see `tasks/012-enrichment-score-calibration.md`.
**Outcome.** —

## D-019 · 2026-08-03 · Cluster membership groups on the driving entity's **uid**, strictly

**Context.** Task 010 Defect 1 requires cluster membership to need a shared driver, grouped on "the normalised entity uid, not the display name". `GraphSignal` (`backend/app/scoring/graph_signals.py:49-66`) carried `driver` (the display **name**) but not the uid — the uid existed as `driver_stat.entity_uid` inside `compute_signals` and was discarded.
**Options.** (a) group on the casefolded display name — no model change, but silently groups on exactly the field the task says not to group on, and merges two distinct entities that share a name; (b) surface the uid on `GraphSignal` and group on it strictly, so an item with no uid can never join a cluster; (c) uid when present, casefolded name as a fallback.
**Decision.** (b). Agent (auto). `GraphSignal.driver_uid` added and set from `driver_stat.entity_uid` — a value already computed, so **no new graph query, no re-projection, no Neo4j change** (the task's constraint holds). `DigestItem` carries `driver` + `driver_uid`; only `driver_uid` is a grouping key. The name fallback (c) was rejected: it reintroduces display-name grouping through a side door, and "no coherent cluster" is an explicitly valid result, so failing closed costs nothing.
**Consequences.** An item whose signal did not fire (`driver_uid is None`) cannot be a cluster member, regardless of its `convergence` value. `coherent_cluster()` in `sections.py` is the single grouping function (no `ClusterStrategy` abstraction, per the task's constraint). Ties break on group size → summed graph score → lowest uid, so selection is deterministic across runs.
**Outcome.** —

## D-020 · 2026-08-03 · The coherence decision is made once, in `sections.py`, and carried on `DigestData`

**Context.** Two places decided "did a convergence fire?": `sections.build_sections` (which selects the weak-signal items) and `posts.generator.weak_cluster` (which re-derived it with its own `convergence > 0` filter). Two filters that must agree is how they drift apart.
**Options.** (a) leave both and fix each; (b) decide once in `sections.py` and record the answer on `DigestData` for the generator to read.
**Decision.** (b). Agent (auto). `DigestData.weak_driver` holds the shared driving entity's name — `""` means no coherent cluster. `weak_cluster()` now returns `(data.weak_signals, bool(data.weak_driver))` and re-derives nothing. New setting `WEAK_CLUSTER_MIN_ITEMS` (default **2**) in `backend/app/core/config.py`, per the task's "no magic numbers"; `build_sections` resolves it from settings when not passed, so existing callers and tests are unaffected.
**Consequences.** A convergence claim is now impossible without a non-empty `weak_driver`, and the label / source count / "converging" wording all key off that one value. `WEAK_CLUSTER_MIN_ITEMS` is documented in-code as a **coherence floor, not a scoring threshold** — lowering it to manufacture a cluster is the failure D-014 forbids, and the comment says so.
**Outcome.** —

## D-021 · 2026-08-03 · Draft honesty: attribute the lead interpretation, disclose the tier on every surface

**Context.** Task 010 leaves two presentation choices open. (i) The cluster-level `why_it_matters` "must be attributable — either label it as such or omit it". (ii) D-016 ruling D requires an `archive`-tier cluster to state its tier, but not where or in what words.
**Options.** (i) omit the lead interpretation entirely — safest, but drops the only reading available and leaves the piece with facts and no thesis; or label it explicitly as the lead item's. (ii) disclose on Medium only (the long-form surface) vs. on all three; disclose on the converged path only vs. on both.
**Decision.** (i) **label it**: the line now reads "AI Verkenner's reading of the FIRST item above only — not a claim about the whole cluster — …", and Medium lists interpretations per item (`- On *<title>*: …`). (ii) disclose on **all three surfaces and both paths**, via `_tier_note()`, which returns `""` when no archive-tier item is involved — so the line appears only when it is true. Agent (auto).
**Consequences.** The wording names AI Verkenner as the author of the interpretation rather than the publisher, so the FACT/INTERPRETATION invariant holds even when a reader skims. On X the tier note is a thread line, not the hook — the hook has no room under `X_CHAR_LIMIT`. A test asserts the disclosure is absent on a `horizon_signal` cluster, so it cannot decay into boilerplate.
**Outcome.** —

## D-022 · 2026-08-03 · Fixed a pre-existing date-overflow bug in `posts_fixtures.py`

**Context.** The backend suite could not reach its 174-passed baseline today: 18 tests failed with `ValueError: day 33 must be in range 1..31`. Cause is `period_end=_BASE.replace(day=_BASE.day + 6)` in `backend/tests/posts_fixtures.py`, where `_BASE = now - 7 days`. It raises whenever `_BASE` lands after the 25th — pre-existing, unrelated to task 010, and verified as untouched context in this session's diff.
**Options.** (a) leave it and report the suite as red — the acceptance criterion (green suite) becomes unreachable; (b) fix it (`_BASE + timedelta(days=6)`) as incidental, out-of-task repair.
**Decision.** (b). Agent (auto). Test-fixture only; no production code involved.
**Consequences.** The "174 passed, 1 skipped" baseline recorded in HANDOFF.md was **date-dependent** — it was true on 2026-07-21 (base = 14 July) and would have failed on roughly the last five days of any month. The suite is now calendar-independent. This also means the baseline was never re-verified during the 13-day review-gate stall; it happened to be re-checked only because this session ran it.
**Outcome.** Fixed. Suite: 181 passed, 1 skipped, 0 failed.

## D-023 · 2026-08-03 · Verification ran `build_digest_data` directly, not the `digest` + `posts` CLI

**Context.** Task 010 asks for verification over `--days 7`, 2026-07-14 → 2026-07-21. The corpus was last written 2026-07-21 and today is 2026-08-03, and neither `app.cli digest` nor `app.cli posts` accepts a `--now`/as-of flag (`backend/app/cli.py:139-217`) — both use `datetime.now()`. Running them as written would select an **empty** 07-27 → 08-03 window (falling back to the whole corpus), i.e. not the window the task names. `app.cli digest` also makes the composition LLM call, which is billable and irrelevant to this defect.
**Options.** (a) run the CLI as written and verify against a different window; (b) add a `--now` flag to the CLI — production surface with no task file calling for it; (c) drive `build_digest_data(..., period_days=7, now=<pinned>)` + `generate_posts` directly — the exact code path `_cmd_posts` uses, minus the digest-row lookup, and explicitly documented as LLM-free.
**Decision.** (c). Agent (auto). Run from the repo root with `PYTHONPATH=backend` and `DATABASE_URL` pointed at `data/dev_corpus.db` (D-006). Zero LLM spend. (b) was rejected as unsanctioned scope; it is a reasonable future task, since the absence of an as-of flag makes any historical window unreproducible from the CLI.
**Consequences.** Reproduced the window exactly: `2026-07-14 16:28 → 2026-07-21 10:45`, 220 events, body 34 / noise 186 (the 07-21 run recorded body 34 / noise 187). Regenerated drafts were written to `outputs/posts/` stamped **2026-08-03** rather than overwriting the `2026-07-21-*` files, so the review's "before" evidence survives beside the "after". `outputs/` is git-ignored, so neither is committed. **Also corrected a false premise in the task prompt:** it stated the graph was "almost certainly EMPTY" after a `down -v`. It was not — Neo4j held 2130 nodes / 3666 relationships / 246 Events before any action this session. `graph-reindex` was run anyway (idempotent, free, ADR 0001) and rebuilt from the same 246 enriched Events.
**Outcome.** Done.

## D-024 · 2026-08-03 · Finding (not a change): the largest coherent cluster is a **hub**, so the claim is still overstated

**Context.** With shared-driver grouping in place, the 2026-07-14 → 07-21 window produces a cluster that is coherent by construction but whose driving entity is **OpenAI** — the corpus's single loudest entity (D-015: 7 sources / 18 mentions / degree 23). The resulting hook reads *"OpenAI is quietly converging across 7 independent sources"*, and the Medium title is *"Weak Signal of the Week: OpenAI"*.
**Options.** (a) add a driver-eligibility rule (suppress hubs, require a minimum IDF, exclude generic concept nodes) so a quieter entity wins; (b) select something other than the largest group; (c) implement Task 010 exactly as specified, record the residual as a finding, and escalate.
**Decision.** (c). Agent (auto) — **no code written for this**. (a) means changing convergence scoring, which Task 010's non-goals forbid ("no new graph queries", "do not change GRAPH_MIN_SOURCES or any threshold"). (b) means substituting the specified rule — the task says "the cluster is the **largest group** whose members share a driver". Both would be silent scope changes of exactly the kind `docs/AGENT_ADDENDUM.md` §5 names as the most dangerous failure mode on this project, only in the helpful direction rather than the threshold-relaxing one.
**Consequences.** Measured over the window's horizon quadrant: **185 items, 84 with `convergence > 0`, resolving to 30 distinct drivers** — so the review's diagnosis (items converging on unrelated entities) is **confirmed**, and grouping is the right fix. But the group-size distribution is hub-shaped: OpenAI 12 · "Large language models" 7 · Microsoft 7 · Google 7 · "AI" 6 · "LLM" 5 · fine-tuning 4; 17 groups reach ≥2 and 13 drivers are singletons. "Largest group wins" therefore selects the loudest entity **structurally**, and M5.5's IDF dampening does not prevent it (OpenAI spans 18 of ~246 developments, so its IDF is still ~2.6 and its 7 distinct sources dominate the product). A second, separable defect is visible in the same table: **"AI", "LLM", "LLMs", "Large language models" and "Artificial Intelligence" are five distinct entity uids for one concept** — an entity-normalisation gap that both inflates driver counts and fragments real clusters. Neither is fixed here. Both need a ruling and a task file. **Task 010's own acceptance criteria are met** (no mixed-driver cluster, entity label, driver-scoped source count, tier disclosed, URLs preserved); the weak-signal trio nonetheless remains **held from publication** under D-016 (A) on this evidence.
**Outcome.** Escalated and **ruled — see D-026.** Task 010 Defect 1 accepted; the residual is fixed under tasks 013/014.

## D-025 · 2026-08-03 · Finding: the X hook truncation is caused by URL length, not the cluster label

**Context.** The review (Finding 1) predicted that driver-based labelling would fix the meaningless `Ag…` truncation on X, because "with driver-based grouping the label becomes the entity, which is both correct and short". It did not: the regenerated hook reads `🛰️ Weak signal of the week: Op… — 8 items converging across 7 independent sources…`.
**Options.** (a) fix it here; (b) record it and leave it to the session that owns X-surface validity.
**Decision.** (b). Agent (auto). Task 010 assigns all X character-limit work to Defect 2 ("reuse `_fit_hook`'s contract — do not write a second trimming rule"), which is a separate session.
**Consequences.** Root cause is that `_fit_hook` preserves the suffix intact and the suffix carries a **200-character** lead URL (the VentureBeat slug), leaving ~2 characters for the variable label. The label is now short and correct — `OpenAI`, six characters — and still gets cut to `Op…`. So the review's prediction was wrong about the mechanism, and Defect 2 cannot be closed by trimming prose alone: the hook needs the URL itself accounted for (shortened, moved out of the hook, or the label given priority over suffix length). Recorded so Session 2 does not rediscover it.
**Outcome.** —

## D-026 · 2026-08-03 · Ruling on D-024: the weak-signal objective is *quietest corroborated*, not *largest group*

**Context.** D-024 escalated that shared-driver grouping, implemented exactly as Task 010 specified, selects **OpenAI** — the corpus's loudest entity — producing the self-refuting hook *"OpenAI is quietly converging across 7 independent sources"*. The agent correctly refused to fix it in-session because Task 010's non-goals forbade touching convergence scoring, and escalated instead (`docs/AGENT_ADDENDUM.md` §5 behaving as intended).
**Options.** (a) accept the drafts as they are; (b) suppress hubs with a blocklist only; (c) change the selection objective itself; (d) revert Task 010 Defect 1.
**Decision.** **(c), with (b) as a hard floor.** The defect is in the **specification**, not the implementation — `coherent_cluster()` maximises `len(group)`, and "largest group" optimises for loudness, which is the inverse of what a weak signal is (*corroborated but not yet loud*). The objective becomes: among groups clearing the corroboration bar, select the driver with the **lowest ambient mention count**. A stoplist makes generic concept nodes (`AI`, `LLM`, `Large language models`, …) categorically ineligible as drivers. Task 010 Defect 1 is **accepted and merged** — shared-driver grouping is correct and necessary; only the selection rule was wrong. Christo, 2026-08-03 (recommendation put by the Cowork review session and accepted as stated).
**Consequences.** Two task files written: `tasks/013-driver-eligibility.md` (quietness objective + concept-node stoplist) and `tasks/014-entity-normalisation.md` (one concept, one uid). **Sequencing is load-bearing and non-negotiable: 013 must merge before 014.** D-024 found five uids for one concept (`AI` / `LLM` / `LLMs` / `Large language models` / `Artificial Intelligence`); normalising them *first* would merge them into a single **larger** hub and make "largest group wins" strictly worse. 014 carries a precondition check and a test pinning that the merged canonical node remains stoplisted. Convergence maths, `GRAPH_MIN_SOURCES` and `priority.py` are untouched by both. The weak-signal trio stays **held from publication** under D-016 (A) until 013 lands.
**Outcome.** —

## D-027 · 2026-08-03 · Two operating lessons folded into the agent addendum

**Context.** Two failures this session, neither caused by the code under review. (1) A stale `.git/index.lock` blocked commits on the host: the Cowork sandbox mounts the repo through a Linux VM, ran `git add`/`git commit`, and lacked permission to unlink its own lock — Claude Code diagnosed a "recurring hazard" without being able to attribute it. (2) D-022 found the recorded 174-passed baseline was **date-dependent** and would have failed on the last days of any month, meaning a number carried across sessions as fact was actually a fixture artefact.
**Options.** (a) note both in HANDOFF and move on; (b) encode both as standing rules in the addendum.
**Decision.** (b). Agent (auto) — the addendum exists precisely to hold rules earned from named failures.
**Consequences.** `docs/AGENT_ADDENDUM.md` gains §7 (no git write operations from a mounted/sandboxed environment — staging and committing belong to the host session) and an extension to §4 (recorded test baselines are **re-verifiable claims, not facts**; re-run before citing). The lock incident also means the Cowork session's contribution ends at *files written* — commits are the host's.
**Outcome.** Done.
## D-031 · 2026-08-04 · Ambient mention count threaded from the existing convergence read; unknown volume sorts quietest

**Context.** Task 013's quietness objective needs each driver's ambient corpus volume, with a hard stop condition: *if the mention count is not already threaded to the digest layer and reaching it would require a new graph query, STOP and report*. `ConvergenceStat.mentions` (`backend/app/graph/store.py:27`) is already read by `compute_signals` and was being discarded, exactly like `entity_uid` before D-019.
**Options.** (a) a new graph query per driver — forbidden, and it would duplicate a read that already happened; (b) surface `mentions` on `GraphSignal` and carry it to `DigestItem`, mirroring D-019's uid threading; (c) approximate volume from the items in hand (e.g. count of quadrant items on the driver) — cheap, but it measures the *sample*, not the ambient corpus, and would rank a driver quiet purely because the week's window was thin.
**Decision.** (b). Agent (auto). `GraphSignal.driver_mentions` is set from `driver_stat.mentions` — a value already computed in the same loop — and `DigestItem.driver_mentions` carries it into `sections.py`. **No new graph query, no Neo4j change, no re-projection**; the stop condition was checked and did not fire.
**Consequences.** A missing/unthreaded value is `0`, which sorts as *quietest*. That is safe rather than convenient: on the real path a driver can only reach `coherent_cluster` with `convergence > 0`, which requires `>= GRAPH_MIN_SOURCES` distinct sources, so its mentions are always `>= 2`; a `0` can therefore only mean "hand-built DigestItem" (fixtures) or "no graph signal", and hand-built fixtures then fall through to the pre-existing size/score/uid tie-breaks, which is why the six task-010 tests are unaffected. Verified on the real corpus: mentions range 2–17 over the 30 shared-driver groups.
**Outcome.** —

## D-032 · 2026-08-04 · The corroboration floor is an eligibility gate, and an unnamed driver cannot label a cluster

**Context.** The old rule picked the largest group first and *then* checked `len(best) < min_items`. Under the quietness objective the check has to move: the quietest group is often small, so testing only the winner would reject a valid cluster whenever a below-floor group happened to be quieter.
**Options.** (a) keep the post-hoc check and select over all groups — the quietest singleton would veto every eligible cluster; (b) filter to groups clearing `WEAK_CLUSTER_MIN_ITEMS` first, then select the quietest among them.
**Decision.** (b). Agent (auto). Additionally, a group whose driver name normalises to the empty string is ineligible — an unlabelled cluster can carry no claim, and every surface keys its wording off that label.
**Consequences.** `WEAK_CLUSTER_MIN_ITEMS` remains exactly what D-020 defined (a coherence floor, unchanged at 2); it is now *applied* to every candidate rather than to the winner. Pinned by `test_min_items_still_enforced`: a mentions=1 singleton loses to a mentions=9 pair, and raising the floor above every group yields the honest quiet-week path. On the real corpus 18 of 30 groups are below the floor, so this is load-bearing, not theoretical.
**Outcome.** —

## D-033 · 2026-08-04 · The stoplist is a commented module constant in `config.py` with a full env override

**Context.** Task 013 requires the stoplist "in config where a human can edit it without touching code, and comment why each class of term is there". This repo's config *is* `backend/app/core/config.py` plus env overrides; there is no separate settings file, and introducing a YAML/JSON loader for fourteen strings would be an abstraction before a use case.
**Options.** (a) a new config file format + loader; (b) a commented module-level constant in `config.py`, overridable wholesale by a comma-separated `WEAK_DRIVER_STOPLIST`; (c) env var only, with no default — a fresh clone would then silently allow "AI" to label a weak signal.
**Decision.** (b). Agent (auto). `_DEFAULT_WEAK_DRIVER_STOPLIST` is grouped and commented by class of term (the field itself · model-class nouns · sub-discipline names), and `.env.example` documents the override. Matching normalises both sides through `schemas.enrichment.normalise_entity_name` — the same lower/trim/collapse key entity resolution uses — so the stoplist matches "the normalised driver identity" the task names, and one normaliser stays authoritative.
**Consequences.** No fuzzy matching, no IDF-threshold heuristic (both explicit non-goals). The list is exact-match on the normalised name, so an unlisted alias — e.g. a future "Large Language Model (LLM)" node — passes; Task 014 collapses aliases and carries a test pinning that the merged canonical node stays stoplisted. Stoplisting is **selection-only**: the four stoplisted drivers still appear in the graph, in scoring and in every other digest section; on the real corpus they cost the weak-signal path four groups (`AI` 7 items, `LLM` 5, `LLMs` 3, `Large language models` 7, `Artificial Intelligence` 3).
**Outcome.** —

## D-034 · 2026-08-04 · The selection audit trail is an INFO log line, not a new CLI or `DigestData` surface

**Context.** Task 013 asks for the chosen driver's stats (mentions, distinct sources, group size) "in the run output so the choice is auditable". Nothing on `DigestData` carried them, and `app.cli` already configures `logging.basicConfig(level=INFO)` (`backend/app/cli.py:223`).
**Options.** (a) add fields to `DigestData` and print them from `_cmd_posts`/`_cmd_digest` — two new surfaces plus a dataclass change, for diagnostics; (b) log at INFO from `coherent_cluster`, where the decision is made; (c) both.
**Decision.** (b). Agent (auto) — the smallest change that satisfies the requirement, and it reaches every caller (CLI, API, scripts) rather than only the two CLI commands.
**Consequences.** `python -m app.cli posts` now prints `weak signal driver: 'X' (uid=N) — mentions=…, distinct sources=…, group size=…; quietest of E eligible group(s) out of D shared-driver group(s)`, and the quiet-week path logs why nothing was selected. `sections.py` gains a module logger; it stays a pure function (the log is the only side effect). If a persistent audit record is wanted later, the fields belong on `DigestData` — deliberately not built now.
**Outcome.** —

## D-035 · 2026-08-04 · Incident: the 2026-07-21 draft files were overwritten during verification, and reconstructed

**Context.** The real-data verification passed `generated_at=NOW` (the pinned 2026-07-21 window end) to `generate_posts`, and `write_outputs` names files by that stamp. It therefore **overwrote the six original `outputs/posts/2026-07-21-*.md` drafts** — the review's "before" evidence for the M7.5 defect. `outputs/` is git-ignored, so there was no version to restore. D-023 had avoided exactly this by stamping its regeneration 2026-08-03.
**Options.** (a) note the loss and move on — the reviewed content is quoted in `docs/reviews/2026-07-25-m7.5-draft-review.md` and in D-024/D-025; (b) reconstruct the pre-Task-010 drafts by running the same LLM-free path from a `HEAD~1` worktree over the unchanged corpus, and keep them under a name that cannot be mistaken for the originals.
**Decision.** (b), and report it. Agent (auto). This session's output was renamed to `2026-08-04-*`; the reconstruction is written as `2026-07-21-reconstructed-*`. The reconstruction reproduces the defect exactly (8 weak-signal items, hook *"New repo: MisterBooo/llm-interview-questions is quietly converging across 11 independent sources"*), which is the evidence the comparison needed.
**Consequences.** Three files now sit side by side for review: `2026-07-21-reconstructed-*` (pre-010, incoherent), `2026-08-03-*` (post-010, coherent but hub-labelled "OpenAI"), `2026-08-04-*` (post-013, "Firefox"). The reconstruction is generated from HEAD~1 code, not the original binaries, and is labelled as such — it is evidence of the same code path, not the artefact the 2026-07-25 review read. **Standing lesson:** any regeneration over a historical window must stamp the output with *today's* date, never the window's, because `write_outputs` treats the stamp as the filename key. Unrelated but same theme: this session re-verified the test baseline in a throwaway `git worktree` at HEAD rather than stashing, so the working tree was never disturbed.
**Note (concurrency).** Three other sessions (tasks 010 S2, 011, 012) were editing the same working tree at the same time, and at least one of them also regenerates drafts over this window; the overwrite is attributed to this session's 12:18 run on file mtimes, but a concurrent run could have destroyed the same files independently. The same concurrency produced a **decision-number collision**: the Task 010 S2 CHANGELOG entry references `[D-028]` / `[D-029]` for its own (unrelated) choices, while D-031–D-036 here are task 013's. Whoever merges must renumber one block — the log is append-only, so the fix is a renumber-and-note, not an edit of intent.
**Outcome.** Reconstructed. Originals lost.

## D-036 · 2026-08-04 · Finding (not a change): the quietest eligible driver is `Firefox` — coherent, quiet, and only marginally an AI signal

**Context.** With task 013 in place the 2026-07-14 → 07-21 window selects `Firefox` (uid 561): 2 ambient mentions, 2 distinct sources, 2 items — *"Firefox in WebAssembly"* (Simon Willison, an AI-assisted WASM port) and *"Mozilla speeds Firefox release schedule to biweekly"* (The Register, a release-cadence story with no AI content). The acceptance criteria are met — not stoplisted, not OpenAI/Microsoft/Google, deterministic, tier disclosed, URLs preserved.
**Options.** (a) widen eligibility or add a topicality gate to reach a more satisfying driver; (b) record the finding and leave the rule alone.
**Decision.** (b). Agent (auto) — no code written for this. (a) is precisely the "helpfully relax the rule to manufacture a better-looking result" failure `docs/AGENT_ADDENDUM.md` §5 names, and topicality is nobody's task file.
**Consequences.** Two observations for the review gate. **First**, the second item is off-topic for an AI intelligence product, and it comes from The Register's site-wide feed — one of the three whole-publication feeds D-017 measured as the source of every off-topic item in the corpus. This reads as **corpus scope (Task 011), not selection**: a quietness objective faithfully surfaces whatever quiet corroboration exists, including noise the registry let in. **Second**, the quiet end of the distribution is densely tied — three groups sit at exactly mentions=2 / 2 items (`Firefox`, `agents`, `distribution shift`), so the summed-`graph_score` tie-break, not quietness, decides the winner among them. Deterministic and stable, but the margin is thin enough that a small corpus change will move the answer; a future task may want a *topical* eligibility signal (the enrichment category/tags are already on `DigestItem`) rather than a louder threshold. Neither is fixed here.
**Outcome.** —

## D-037 · 2026-08-04 · Two of the eight "zero-yield" sources are healthy and stay enabled; the audit's framing was wrong

**Context.** Task 011 defect 2 instructs: "Investigate the other seven and either fix the URL or disable with a reason." Probing all 28 registry entries through the real fetchers (2026-08-04, read-only, no persistence, no spend) shows that instruction rests on a false premise. **LlamaIndex Releases** fetches 30 releases fine (newest `v0.14.23`, 2026-06-24) and **Eugene Yan** serves 212 entries (newest 2026-06-21). Neither is broken; both simply publish less often than the recency window, so nothing survives `apply_recency_cap` and they read as "0 rows" in the corpus.
**Options.** (a) follow the instruction literally and disable both with "yields nothing" as the reason; (b) fix a URL that is not broken; (c) leave both enabled, record the real cause, and make the health view state it.
**Decision.** (c). Agent (auto). Disabling a working source because a 7-day window outran its publishing cadence would *remove real coverage* to satisfy a metric — the same "helpfully make the number look right" failure `docs/AGENT_ADDENDUM.md` §5 names. Both entries carry an inline comment recording the probe evidence so the next reader does not re-diagnose them as dead.
**Consequences.** Six of the eight named sources are resolved as the task intended (2 disabled, 1 URL fixed, 3 token-gated); two are deliberately left enabled and now surface as `stale-window` rather than as failures. The acceptance criterion "every one of the eight sources is either fixed or explicitly disabled" is met in substance but **not literally** — this needs a human ruling at the review gate. If Christo wants a strict reading, disabling both is a two-line YAML change.
**Outcome.** —

## D-038 · 2026-08-04 · Anthropic News and Neo4j Releases are disabled, not substituted

**Context.** Two entries are genuinely dead. `https://www.anthropic.com/news` is an HTML page: HTTP 200, parses to zero entries, so it looked healthy while contributing nothing for the whole corpus. `neo4j/neo4j` stopped publishing GitHub **Releases** in 2017 (newest `3.3.0-beta01`, 2017-09-15) although the repo is actively **tagged** (`2026.06.0`, `2026.05.0`, …), and the `github_releases` fetcher reads `/releases`.
**Options.** (a) Anthropic: point at `status.anthropic.com/history.rss`, which does exist and does parse; (b) Neo4j: switch the fetcher to read `/tags`; (c) disable both with an inline reason recording the evidence.
**Decision.** (c) for both. Agent (auto). The Anthropic status feed is **incident history, not product news** — a different source wearing the same name, which is a substitution rather than a fix and would quietly change what the registry claims to cover. A tags-based fetcher is a new fetcher and no task file calls for one. Seven candidate Anthropic feed paths were probed (`/news.rss`, `/news/feed`, `/rss.xml`, `/news/rss.xml`, `/feed.xml`, `/atom.xml`, `/news/index.xml`) and all 404.
**Consequences.** The enabled count drops 28 → 26. Anthropic — a frontier lab, `trust_level: high` — is now **uncovered**, and that is a real gap in an AI early-warning system, visible rather than silent. Re-enabling needs either a real feed or a sanctioned non-feed fetcher. **LangChain Blog was genuinely fixable** and was fixed: `blog.langchain.dev/rss/` now 302s to an HTML page, the feed moved to `https://www.langchain.com/blog/rss.xml` (verified: 100 entries; 10 within the window on the live run).
**Outcome.** —

## D-039 · 2026-08-04 · Fetch health is a `SourceHealth` SQLite table upserted by the storage pipeline, not run-local state

**Context.** Task 011 requires `sources --health` to print "last successful fetch, items last run, consecutive zero-yield runs" — all three span runs, so they cannot live on the in-memory `IngestionRun`. `new_count` is also only knowable *after* `persist_new_items`, so the orchestrator cannot record it.
**Options.** (a) a JSON/state file beside the DB; (b) a `SourceHealth` table in SQLite, upserted by name exactly like `Source`; (c) derive health at read time by querying `raw_item` timestamps per source.
**Decision.** (b). Agent (auto). SQLite is already the system of record (ADR 0001) and `Source` is already upserted by name, so this is the existing pattern rather than a new one. (c) cannot work at all: a source that stored **zero** rows leaves no rows to derive from — precisely the case being surfaced. The write happens in `ingest_and_store` *after* the records are committed, so a health write can never affect what was stored.
**Consequences.** New table `source_health` (created by `init_db`; no migration tooling in this project, and it is additive). `run_ingestion` alone does **not** record health — only the storage pipeline does — so a bare orchestrator call stays side-effect-free and testable. `sources --health` calls `init_db()`, so it works on a fresh clone and reports every enabled source as `never-run`. Health is **not** exposed on the FastAPI/dashboard surface: no task file calls for it.
**Outcome.** —

## D-040 · 2026-08-04 · "Zero yield" is four different diagnoses, and the health view names which one

**Context.** D-017 reported eight enabled sources contributing "0 rows". Treating that as one condition is what made the defect hard to act on: the live probe shows the same zero arises from four unrelated causes, and three of them are not faults.
**Options.** (a) report a single boolean per source ("yielded / did not yield"), as the task file's wording implies; (b) classify the zero and state the reason on every line.
**Decision.** (b). Agent (auto). `app/ingestion/health.py` classifies each source as `ok` · `error` (the fetch raised) · `no-items` (fetch succeeded, parsed to zero entries — the genuinely broken case) · `stale-window` (fetched fine, nothing inside `SOURCE_MAX_AGE_DAYS`) · `no-token` (a `github_*` source with no `GITHUB_TOKEN` — skipped by ADR 0002 design) · `never-run`. `SourceRunResult` keeps `fetched_count` and `item_count` separate for the same reason, and the token rule has one owner (`needs_github_token` in the fetcher module) rather than being re-derived from the source type inline. `zero_yield` counts items that reached **storage** (`item_count`), not items fetched.
**Consequences.** A missing token reads as "needs GITHUB_TOKEN (skipped by design, not broken)" and a quiet blog as "healthy fetch: N item(s) returned, none within the recency window" — neither sends the human to fix a working URL. Token-gated sources are still *counted* in the zero-yield streak and still *appear* in the loud run-summary warning; only the stated reason differs. That is deliberate — an early-warning system with four uncovered GitHub-intelligence sources should say so every run.
**Outcome.** —

## D-041 · 2026-08-04 · Finding (not a change): the recency cap is the dominant cause of zero yield, and D-017's list of eight is wrong in both directions

**Context.** Ground-truth probe of all 28 registry entries, 2026-08-04. The effective `SOURCE_MAX_AGE_DAYS` in this environment is **7**, injected by direnv — not the `30` that `config.py` documents as the default and that the `sources.yaml` header implies. Nothing in the repo records the override, and no `.env` exists at the repo root.
**Options.** (a) change the cap or the default to make more sources yield; (b) record the finding and leave both alone.
**Decision.** (b). Agent (auto). Changing a tuning constant to improve a coverage statistic is out of scope for this task and is the manufacture-a-result failure again. The cap is now *visible* in the health output instead, which was the actual defect.
**Consequences.** Two corrections to D-017. **First, the list is short:** `Qdrant Releases` and `VentureBeat AI` also yield zero under a 7-day window, and were never named — 11 sources are flagged on a live 3-run probe, not 8. **Second, the list is wrong:** two of its eight entries (LlamaIndex Releases, Eugene Yan — see [D-037]) are healthy. The corpus consequence is real: with `SOURCE_MAX_AGE_DAYS=7`, any source publishing monthly is structurally invisible, which biases the corpus toward high-frequency publishers — the same publishers Defect 1 just narrowed for being noisy. **Recommendation for Christo:** this is a tuning decision, not an agent one. Raising the cap to 30 (its documented default) would restore LlamaIndex, Eugene Yan, Qdrant Releases and VentureBeat AI at the cost of a larger enrichment bill; the health view now makes the trade-off measurable before paying it. Also worth recording the override where a reader will find it — `.env.example` documents the *name*, not that this machine sets it to 7.
**Outcome.** —

## D-047 · 2026-08-04 · Task 013 review: the *quietest* objective is right, but the eligibility floor is too low

**Context.** Task 013 attempt 1 swapped the weak-signal objective from *largest group* to *quietest corroborated driver* (D-026) and added a concept stoplist. Both work: `OpenAI` (17 mentions / 12 items) now sorts last and the AI/LLM concept family is excluded. But the winner was **`Firefox` — 2 mentions, 2 distinct sources, 2 items**, with three groups tied at that floor, and D-036 found one of its two items has no AI content at all.
**Options.** (a) accept Firefox and treat topicality as the fix; (b) revert to *largest group*; (c) keep the objective and raise the eligibility floor; (d) replace minimisation with a lift/ratio measure (sources per mention).
**Decision.** **(c).** `GRAPH_MIN_SOURCES = 2` and `WEAK_CLUSTER_MIN_ITEMS = 2` (`backend/app/core/config.py:153,174`) are the lowest values that are not "one", so *minimising* ambient volume bottoms out at the corroboration floor **by construction** — Firefox is the rule's fixed point, not an unlucky draw. A weak signal needs **enough corroboration to be real AND low ambient volume**; attempt 1 delivered only the second half. (d) was considered and rejected for now: a ratio adds a tuned quantity where a floor is simpler, auditable, and sufficient — revisit only if the floor proves inadequate. (b) is a regression to a self-refuting claim. Christo, 2026-08-04 (recommendation put by the Cowork review session and accepted as stated).
**Consequences.** Task 013 gains **Defect C**: new `WEAK_DRIVER_MIN_SOURCES` (default **3**) and `WEAK_CLUSTER_MIN_ITEMS` raised **2 → 3**, both **selection-only**. **`GRAPH_MIN_SOURCES` is explicitly NOT changed** — it is the global floor inside `graph_signals` below which a convergence contribution is zeroed, and raising it would alter convergence scoring product-wide, which D-026 ruled out; a test must prove it untouched. Defects A and B are **accepted as implemented** and must not be reverted. Expected eligible set after the floor (from attempt 1's distribution, stoplist applied): OpenAI 12 · Microsoft 7 · Google 7 · fine-tuning 4 · Claude Code 3 — so the winner should be `fine-tuning` or `Claude Code`. That is an **expectation, not an acceptance criterion**. An honest empty week remains a correct outcome; the floor must never be lowered to manufacture a cluster.
**Outcome.** —

## D-050 · 2026-08-04 · Task 011 review: ACCEPTED at the gate, with two cadence comments added to complete the D-048 criterion

**Context.** Task 011 (source scope + fetch health) was implemented by another session and Christo asked for it to be accepted at the review gate, the acceptance criterion having been amended in place by [D-048]. This review verified it against ground truth rather than against the implementing session's report — the working tree carries four sessions' interleaved work, so nothing was taken on faith.
**Options.** (a) accept as-is; (b) accept and close the one gap found; (c) reject and send back.
**Decision.** **(b) — ACCEPTED.** Both defects verified independently and both hold. Agent (auto) for the two-comment fix, which is a "do now" item under `AGENT_ADDENDUM.md` §3: no judgment call, no cost, reversible.
**Consequences.** **What was verified live (LLM-free, $0, network only):** all four replacement/fixed feed URLs return well-formed feeds with the entry counts the task claims — The Register — AI/ML **50**, MIT TR — AI **10**, HN AI/LLM ≥100 **20**, LangChain Blog **100** — and their newest items are on-topic. The three Defect-1 blocks match the task file verbatim; no unauthorised registry entry was touched. The health path was exercised end to end on a **copy** of `data/dev_corpus.db` (the baseline corpus is byte-identical and gained no `source_health` table, which matters because Task 012's measurement baseline depends on it): a real 26-source fetch classified **zero sources as `no-items`** — the genuinely-broken state — which is the direct evidence that the dead-URL cases are resolved. `stale-window` matched exactly the four sources D-041 named (Eugene Yan 212 entries, LlamaIndex 30, Qdrant 30, VentureBeat 7); `no-token` correctly captured all seven `github_*` sources with their own reason; the 11 zero-yield warnings printed non-fatally after a successful run. D-041's premise correction is confirmed: the effective `SOURCE_MAX_AGE_DAYS` is **7**, not the documented 30. `backend/tests/test_source_health.py` is 10/10 green and contains all four named tests; Task 011's blast radius (8 suites) is 56/56 green; the full backend suite settles at **215 passed / 1 skipped / 0 failed** — it flapped between runs only because three other sessions were editing the tree mid-run, which is a tree artefact, not a defect. **The one gap, now closed:** D-048's amended criterion requires every zero-yield source to be *fixed, disabled with a reason, or explicitly retained with its cadence recorded*. Four sources are retained; only two (LlamaIndex, Eugene Yan) carried a cadence comment. Cadence comments were added for **Qdrant Releases** (newest v1.18.3, 2026-07-17 — a normal gap for a release feed) and **VentureBeat AI**. **New finding on VentureBeat AI:** it parses cleanly but its newest item is **2026-05-19**, 2.5 months stale for a daily publisher — that reads like a feed that stopped updating rather than low cadence. Left enabled (it fetches cleanly, and disabling on suspicion deletes coverage) with a dated watch-note in the YAML: if it is still frozen at 2026-05-19 at the next review, it is a dead feed needing a URL fix or a disable. **Follow-ups inherited, not resolved here:** the `SOURCE_MAX_AGE_DAYS` env/docs drift (7 vs 30) is Christo's tuning call per D-048; renaming a source orphans its `source_health` row, so the three renamed feeds start their history fresh — correct but worth knowing.
**Outcome.** Task 011 accepted; status updated in the task file.

## D-051 · 2026-08-04 · Fixtures built at the old floor were raised to it, not exempted from it

**Context.** Task 013 defect C raises `WEAK_CLUSTER_MIN_ITEMS` 2 → 3 and adds `WEAK_DRIVER_MIN_SOURCES` = 3. Nine tests failed immediately, all for the same reason: their fixtures were built when 2 items / 2 sources was a valid convergence — `test_digest._seed` (2 converging RAG developments from 2 sources, reused by `test_posts_integration`), the six Defect A/B tests in `test_driver_eligibility.py`, and two membership tests in `test_cluster_coherence.py`.
**Options.** (a) pass explicit floors of 2 everywhere so the fixtures keep passing under the old rule; (b) raise the fixtures to the new floor; (c) weaken the floor until the suite is green.
**Decision.** **(b), with (a) only where the test is genuinely about something else.** Agent (auto). (c) is the failure mode this project's rules exist to prevent — the floor is the product decision D-047 made, and a test that forces it down would invert the ruling. (a) applied everywhere would leave *no* test exercising the shipped defaults end to end.
**Consequences.** `test_digest._seed` now creates **three** converging RAG developments from **three** distinct sources (a new `src4`), so the fixture's own claim — "a genuine weak signal" — stays true under the new rule instead of being grandfathered; `total_events`/`item_count` assertions moved 6/4 → 7/5 and `test_posts_integration` asserts the third link. `test_driver_eligibility._driven` defaults to three publishers, because those tests are about the *ordering* (quietest wins, stoplist excludes, ties resolve) and need selectable candidates before ordering can be observed. `test_cluster_coherence` clusters moved to three items on three publishers; those tests pin **membership**, which is unchanged. **No production threshold was lowered and no assertion was deleted.** The suite went 218 passed / 1 skipped / 0 failed. Standing note: when a floor moves, fixtures pinned below it are evidence about the old rule — raise them or state explicitly why they are exempt.
**Outcome.** —

## D-052 · 2026-08-04 · Finding (not a change): the winning cluster's third item is a passing mention

**Context.** With the floor in force the weak signal becomes **`Claude Code`** (5 mentions / 4 distinct sources / 3 items) — the outcome D-047 predicted. Reading the three items: two are substantively about Claude Code (a Bun/Rust port shipped in v2.1.181; a tool built with it), the third is The Register's NextBSD revival story, which references Claude Code once, as one component of the revival.
**Options.** (a) add a mention-weight or topicality gate so passing mentions cannot join a cluster; (b) record it as a finding and leave the cluster as selected.
**Decision.** (b). Agent (auto) — Task 013's non-goals explicitly exclude a topicality gate on cluster items ("D-036's Mozilla item is corpus scope and is Task 011's job, not this one"), and adding one would be the silent scope change `AGENT_ADDENDUM.md` §5 names.
**Consequences.** This is **materially better than the D-036 Firefox case**, which is worth stating precisely: there, one of two items had *no* AI content at all. Here all three items genuinely reference the driver, so the cluster is honest — the third link is simply thinner than the other two, which makes "3 items converging" true but not evenly weighted. Whether a passing mention should count toward the item floor is a **mention-weight** question, separable from both the floor (defect C) and corpus scope (Task 011), and it needs its own ruling before anyone should treat it as a defect. The third item also comes from The Register's whole-publication feed — the same D-017 source-scope pattern as D-036, now narrowed by Task 011's feed replacements but visible in this pre-011 corpus.
**Outcome.** —

