# HANDOFF — AI Verkenner

> Volatile state. Overwritten at the end of every session; history lives in git.
> Read this FIRST at the start of every session (see CLAUDE.md session protocol).

## STATUS: GO — awaiting Christo's review gate

<!-- GO = safe to start new work. NO-GO = fix the stated blocker first. -->

## Where things stand (2026-07-21)

Branch `feat/m7.5-broad-run`. **M7.5 STEP 3 (the real broad run) has now been executed.**
Milestone status is still **unchanged pending Christo's review** — nothing here flips it.

- **Corpus** (`data/dev_corpus.db`): **246 events, 246 enriched, 0 unenriched**
  (243 `llm`, 3 `fallback`). All 7 curated `github_*` sources ingested with `GITHUB_TOKEN`.
- **Digest 3** generated (`--days 7`, 2026-07-14 → 2026-07-21): `body=34 noise=187 weak=8
  graphrag=True`.
- **Posts**: 6 drafts in `outputs/posts/` + 6 create-only vault notes in
  `~/github_repos/knowledge-vault/00-Inbox`. `convergence=True`.
- **M7 Q2 answered — YES.** Cross-publisher convergence fires on a real corpus:
  **107 entities span ≥2 distinct sources, 31 span ≥3** (OpenAI 7, Anthropic 6, Google 4).
  See D-015.
- **Tests green**: backend **174 passed, 1 skipped, 0 failed**; frontend **10 passed**.

## Next steps

1. **Christo reviews the three drafts** in `outputs/posts/` (weak-signal X / LinkedIn / Medium)
   plus the Noise Report trio. No merge, push, or status flip before that.
2. Judge the **cluster-coherence concern** (below) — it is the one substantive quality issue.
3. Fill in `docs/m7.5-broad-notes.md`: it still says "blocked on the API key" and its recipe
   (`cd backend && python -m app.cli run`) is **wrong** — with a relative `DATABASE_URL` the CLI
   must run from the **repo root** with `PYTHONPATH=backend` (see D-006).
4. Fix the orphaned-backlog defect (D-013) under its own task file.
5. M8 calibration: the empty horizon quadrant (D-014).

## Open questions / blockers

- **Cluster coherence (needs a human call).** The weak-signal cluster is technically valid —
  8 items, 9 independent publishers — but thematically loose: an enterprise-agent survey sits
  beside a PPO trust-region paper, a K-12 tutor launch, a vibration-energy-harvester benchmark
  and a 3D-molecule benchmark. They share only a generic "LLM" hub. Convergence is firing on a
  broad topic rather than a specific entity, so the "converging" claim is weaker than it reads.
- **Cluster label is an article headline, not an entity.** The cluster is titled with the
  VentureBeat headline, which makes the LinkedIn line read "<full headline> is quietly
  converging across 9 independent sources". On X it truncates to a meaningless `Ag…`.
- **`horizon_signal` is empty** (`archive` 208 / `operational_update` 37 /
  `immediate_priority` 1). Weak signals still worked — they are selected by the
  `is_weak_signal` flag and admit `archive` items, so the section is NOT empty. Per Christo's
  standing ruling `priority.py` is untouched (D-014).
- **Convergence image is a placeholder** — `matplotlib`/`networkx` are not installed; the draft
  carries a "screenshot the Cosmograph Network view" pointer instead.
- **Event 209 fell back twice** (retry included) — a persistently malformed item, not transient.
- Corpus relevance noise: the Noise Report's second entry is an MIT Tech Review article about
  perimenopause — a source-registry relevance question, not a code defect.
