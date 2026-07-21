# HANDOFF — AI Verkenner

> Volatile state. Overwritten at the end of every session; history lives in git.
> Read this FIRST at the start of every session (see CLAUDE.md session protocol).

## STATUS: GO

<!-- GO = safe to start new work. NO-GO = fix the stated blocker first. -->

## Where things stand (2026-07-21)

Branch `feat/m7.5-broad-run`. **M7.5 milestone status is unchanged and awaiting Christo's
review — nothing here flips it.**

- **The M7.5 STEP 3 broad run is still incomplete.** It was terminated by a **system restart**
  (`kern.boottime` 07:48:23) mid-enrichment; its last write was 07:41:36. Not sleep, not OOM,
  not a signal — see D-002 for the ruling-out evidence.
- **Corpus** (`data/dev_corpus.db`, the source of truth): 199 events, 102 enriched
  (100 `llm`, 2 `fallback` dated 2026-06-22), **97 unenriched** — the remaining work.
- **Test suites are green on default settings**: backend **168 passed, 1 skipped, 0 failed**;
  frontend **10 passed**. They were 5-red at commit `8d441fa` purely from fixture time-rot
  (D-004), fixed test-only in D-005. No production code was changed this session.
- **Environment is ready:** `ANTHROPIC_API_KEY` is present via direnv and `config.py:89` falls
  back to it, so the old "blocked on the API key" note in `docs/m7.5-broad-notes.md` no longer
  applies. Isolated stores `m75broad` are up and reachable on **6335** (Qdrant) / **7688** (bolt)
  / **7475** (http); default ports 6333/7687 are closed, so there is no path to the
  `trafficking-intel-*` stack.

## Next steps

1. Resume the run: `python -m app.cli run` (enrichment is incremental — only the 97 unenriched
   events are billed; work already paid for is not repeated).
2. `python -m app.cli digest --days 7`, then
   `python -m app.cli posts --digest latest --vault-dir ~/github_repos/knowledge-vault`.
3. Report the three drafts and whether cross-publisher convergence fires **at corpus level**
   (M7 Q2) to Christo. No merge, no push, no status flip before that review.
4. `docs/m7.5-broad-notes.md` still says "blocked on the API key" — update it once STEP 3
   actually runs.

## Open questions / blockers

- **M7 Q2 remains open:** whether cross-publisher convergence fires on a *real* corpus is still
  unconfirmed. It is confirmed on the synthetic fixture and the M7 digest seed only.
- A restart already killed one run; prefer a detached, resumable invocation.
