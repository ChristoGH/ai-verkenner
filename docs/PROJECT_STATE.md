# AI Verkenner — Project State

> **Living status doc — the single "where are we" source.** Update the date + the moving parts at
> each review gate. For the *roadmap* (what each milestone delivers) see
> [`PHASE_1_PLAN.md`](PHASE_1_PLAN.md); this file is the *current state* only.

**Last updated:** 2026-07-06

## One-line status

Phase 1 ("viable first phase") is ~90% through the milestone ladder. The pipeline runs end to end on
real data; the cross-publisher convergence signal — the project's reason to exist — is validated.
M7 (feedback + GraphRAG digest) is merged to `main`. **M7.5 (post generator) is built and in review**
on `feat/m7.5-post-generator`: a weekly digest projects into human-approved DRAFTS — Weak Signal of
the Week + Noise Report — for **X, LinkedIn, and Medium** (draft-only, no auto-posting), also written
into the Obsidian vault (create-only). The one remaining spend — the M7.5/M8 broad-corpus run that
re-confirms cross-publisher convergence in a real digest — is **deferred** (see the carry-forwards).
Next substantive milestone after review: **M8 (hardening / "viable" gate)**.

## Milestone ladder

| Milestone | State | Commit |
|---|---|---|
| M0 Scaffold | ✅ done | `5d7ec56` |
| M1 Source registry + ingestion | ✅ done | `39ee413` |
| M2 Infra (Qdrant + Neo4j + health) | ✅ done | `5a9e542` |
| M3 Storage + embeddings + semantic dedup | ✅ done | `6fc971b` |
| M4 LLM enrichment + entity/relationship extraction | ✅ done | `2fd5acc` |
| M5 Neo4j projection + graph-aware ranking | ✅ done | `9d09209` |
| M5.5 Convergence quality (hub-dampening) | ✅ done | `63390ce` |
| M6 Dashboard + Cosmograph + real-data smoke | ✅ done | `e001f32` |
| M6.5 Source breadth (GitHub intel + recency cap) | ✅ done, **merged + pushed** | `7a6fb9f` |
| M7 Feedback + GraphRAG digest | ✅ done, **merged** | `ac9219e` |
| M7.5 Post generator (X/LinkedIn/Medium) | ✅ built (offline-green), **in review**; broad run deferred | `feat/m7.5-post-generator` |
| M8 Hardening / "viable" gate | ⬜ pending | — |
| M8.5 Read-only MCP server | ⬜ pending | — |

## Git / publish state

- **`main`:** M7 is merged (`ac9219e`, PR #1). M7.5 work is on the unmerged branch
  **`feat/m7.5-post-generator`** (off `main`); do not merge — it ends at the review gate.
- **Merged feature branches** (`feat/m7-feedback-digest`, `feat/m6.5-source-breadth`, and the earlier
  `feat/m*`) are fully contained in `main` and safe to prune.
- **168 backend tests (+1 skipped) + 10 frontend tests** passing (M7.5 added 24 post-generator tests;
  the skip is the optional matplotlib render path).

## Validated on real data (not just unit tests)

- Scores are defensible; **hype catches marketing/satire**; entity extraction is grounded.
- **Degrade-don't-crash held under a genuine failure** (Qdrant dim drift → hash-only dedup, no
  data loss).
- **Hub-dampening works** (M5.5): `/horizon` stopped ranking "GitHub is everywhere."
- **Cross-publisher convergence works** (M6.5): `/horizon` surfaces NVIDIA / Anthropic / Cursor /
  Claude Code across *independent* publishers; GitHub-intelligence feeds contribute directly.

## Key decisions

- [ADR 0001] Qdrant + Neo4j + Cosmograph adopted; SQLite is source of truth, the stores are
  rebuildable derived indices.
- [ADR 0002] Read-only local MCP surface + curated `github_*` source types (watched list + API,
  not a crawler).
- `priority.py` is the single source of truth for the priority rule (relevance-5 floors to
  immediate_priority).
- Convergence = distinct **independent** sources, IDF-weighted, singleton-suppressed.

## Open questions / carry-forwards

- **Cross-publisher convergence in a real digest — still deferred to the broad run.** M7.5's code is
  proven on a synthetic-convergence fixture *and* on the M7 seed (convergence fires, a real Weak
  Signal of the Week is produced), but the **real broad-corpus run** (28 sources into
  `data/dev_corpus.db`, ~$20–30, then `digest` + `posts`) that re-confirms it end-to-end has **not**
  been run yet — see [`m7-digest-notes.md`](m7-digest-notes.md) Q2. Blocked on (a) local disk (the
  host is at ~100%) and (b) an explicit go-ahead for the spend + isolated Docker stores. Record it in
  `docs/m7.5-broad-notes.md` when run.
- **Feedback rule is latest-action-wins** — transparent and explainable; revisit if a cumulative
  model is ever wanted (out of scope now).
- **Decouple `github_advisories` from the general recency cap** — Early Warning shouldn't expire in
  7 days (M6.5 finding).
- **Star-velocity is seeded but unobserved** — needs a second run to emit deltas.
- **`USER_CONTEXT` is generic** — could be seeded from the Obsidian vault (modest near-term value;
  see the vault assessment) — pragmatic v1 is a hand-written context paragraph.
- **Cost:** ~$15 of Opus per ~120-event run (enrichment); a digest is one cheap composition call.

## Next step (recommended)

1. **Review M7.5** (`feat/m7.5-post-generator`) at the gate — the offline generator, fixtures, image
   placeholder, create-only vault writer, and the `posts` CLI. Then merge.
2. **M7.5/M8 broad run (the one remaining spend).** Free up disk, bring up isolated stores on
   non-conflicting ports (leave `za-corruption-neo4j-1` alone), ingest the full 28-source
   `sources.yaml` into `data/dev_corpus.db`, then `digest` + `posts`; record `docs/m7.5-broad-notes.md`
   (did cross-publisher convergence fire? paste the X + LinkedIn + Medium drafts; flag cost + window).
3. **M8 — hardening / "viable" gate.**
