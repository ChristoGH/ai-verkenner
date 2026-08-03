# HANDOFF — AI Verkenner

> Volatile state. Overwritten at the end of every session; history lives in git.
> Read this FIRST at the start of every session (see CLAUDE.md session protocol).

## STATUS: GO — blocked on one human ruling (D-016 item D)

<!-- GO = safe to start new work. NO-GO = fix the stated blocker first. -->

## Where things stand (2026-08-03)

Branch `feat/m7.5-broad-run`. **No code has changed since 2026-07-21** (last commit `92841f7`).
The 13-day gap was a review-gate stall, not a technical blocker. Two review/analysis sessions have
run since; all output is documentation.

- **Corpus** (`data/dev_corpus.db`): 246 events, 246 enriched (243 `llm`, 3 `fallback`).
  **Last written 2026-07-21 16:14 — now 13 days stale.**
- **Tests**: backend 174 passed / 1 skipped / 0 failed; frontend 10 passed. Unchanged (no source
  file touched since 21 July).
- **M7.5 drafts: HELD from publication.** The weak-signal cluster makes a false converging claim —
  8 items, 1 of which supports the stated thesis. See
  [`docs/reviews/2026-07-25-m7.5-draft-review.md`](docs/reviews/2026-07-25-m7.5-draft-review.md).
  This fails Task 009's own acceptance criterion, so **M7.5 does not pass its gate.**

### Landed since the last handoff (docs only)

- `docs/reviews/2026-07-25-m7.5-draft-review.md` — full draft review, root cause, decisions A–F.
- `tasks/010-convergence-cluster-coherence.md` — cluster coherence + X char limit + noise cap.
- `tasks/011-source-scope-and-fetch-health.md` — three whole-publication feeds + eight silent sources.
- `tasks/012-enrichment-score-calibration.md` — the M8 calibration work, now root-caused.
- `docs/DECISIONS.md` — D-016 (pending ruling), D-017 (registry audit), D-018 (D-014 corrected).
- `docs/m7.5-broad-notes.md` — corrected: it wrongly said "blocked on the API key" and carried a
  run recipe with the wrong working directory (the D-006 trap). Both fixed.

## Next steps

**Blocking, human-only:**

0. **Rule on D-016 item (D)** — is an `archive`-sourced weak signal acceptable under D-014's spirit?
   `horizon_signal` is 0; the quadrant is non-empty only because `HORIZON_CLASSES` admits `archive`.
   Nothing merges until this is answered. Then update D-016 with the ruling and re-attribute it.

**Then, in order:**

1. **Task 010 Session 1** — cluster coherence (blocker for all draft work). Prompt in the task file.
2. **Task 010 Session 2** — X thread char limit + Noise Report cap.
3. **Re-ingest to a current window.** The corpus is 13 days stale and the drafts cover
   2026-07-14 → 07-21. A correct weak signal about a window that closed two weeks ago is still not
   publishable. Use the corrected recipe in `docs/m7.5-broad-notes.md` — **repo root,
   `PYTHONPATH=backend`** (D-006). This run also re-tests D-013: if it is interrupted, the orphan
   defect recurs and will be visible immediately.
4. **Task 011** — source scope + fetch health. Independent of 010; can run in parallel.
5. **Task 012** — enrichment calibration. Independent of 010; needs a cost decision for any
   full-corpus re-enrichment.
6. **D-013** — orphaned-backlog defect, still open, still needs its own task file.

## Open questions / blockers

- **D-016 (D) — the one blocking ruling.** See above.
- **Corpus staleness.** Any publication decision now requires a fresh run first (step 3).
- **Eight enabled sources yield zero rows** (D-017) — Anthropic News points at an HTML page, not a
  feed; LangChain Blog, LlamaIndex Releases, Neo4j Releases, Eugene Yan silently fail; three
  `github_*` may just need `GITHUB_TOKEN`. The registry currently claims coverage the corpus does
  not have. Task 011.
- **`horizon_signal` empty — root cause now known** (D-018, corrects D-014): axis collinearity,
  r(relevance, strategic_potential) = 0.842, `sp` never exceeds `rel + 1`. The quadrant is
  structurally unreachable. `priority.py` remains untouched and is **not** the defect. Task 012.
- **Convergence image is still a placeholder** — `matplotlib`/`networkx` not installed.
- **Event 209 fell back twice** — persistently malformed item, not transient.
- **19 of 266 corpus items (7%) are off-topic**, all from three site-wide feeds (D-017). Existing
  rows are left in place per the URL invariant; they age out of the digest window.
