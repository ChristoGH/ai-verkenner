# AI Verkenner — Project State

> **Living status doc — the single "where are we" source.** Update the date + the moving parts at
> each review gate. For the *roadmap* (what each milestone delivers) see
> [`PHASE_1_PLAN.md`](PHASE_1_PLAN.md); this file is the *current state* only.

**Last updated:** 2026-06-22

## One-line status

Phase 1 ("viable first phase") is ~85% through the milestone ladder. The pipeline runs end to end on
real data; the cross-publisher convergence signal — the project's reason to exist — is validated.
**M7 (feedback + GraphRAG digest) is complete and in review** — the core loop now closes, and the
real-data smoke validated the LLM-composed digest (reads as decisions, honest noise count). The one
deferred check (cross-publisher convergence) rides on the M8 broad-corpus run. Next substantive
milestone: **M7.5 (post generator)**.

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
| M7 Feedback + GraphRAG digest | ✅ smoke done (LLM-composed digest validated), **in review** | `feat/m7-feedback-digest` |
| M7.5 Post generator (LinkedIn/Medium) | ⏳ next | — |
| M8 Hardening / "viable" gate | ⬜ pending | — |
| M8.5 Read-only MCP server | ⬜ pending | — |

## Git / publish state

- **`main`:** published to `origin/main` through the M6.5 consolidation (`a04596a`). M7 work is on
  the unmerged branch **`feat/m7-feedback-digest`** (off `main`); do not merge — it ends at the
  review gate.
- **Merged feature branches** (`feat/m6.5-source-breadth` and the earlier `feat/m*`) are fully
  contained in `main` and safe to prune.
- **146 backend tests + 10 frontend tests** passing (M7 added feedback + digest coverage).

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

- **M7 cross-publisher convergence — pending the M8 broad run.** The smoke validated the digest end
  to end and the LLM-composed narrative reads as decisions (see [`m7-digest-notes.md`](m7-digest-notes.md));
  a persistent dev corpus lives at `data/dev_corpus.db` (gitignored). The one deferred check is
  weak-signal *convergence*, which needs a corpus with publisher overlap — re-confirm on M8's broad
  registry run (M6.5 already proved convergence fires there). API credits are live again.
- **Feedback rule is latest-action-wins** — transparent and explainable; revisit if a cumulative
  model is ever wanted (out of scope now).
- **Decouple `github_advisories` from the general recency cap** — Early Warning shouldn't expire in
  7 days (M6.5 finding).
- **Star-velocity is seeded but unobserved** — needs a second run to emit deltas.
- **`USER_CONTEXT` is generic** — could be seeded from the Obsidian vault (modest near-term value;
  see the vault assessment) — pragmatic v1 is a hand-written context paragraph.
- **Cost:** ~$15 of Opus per ~120-event run (enrichment); a digest is one cheap composition call.

## Next step (recommended)

1. **Run the M7 digest smoke** (acceptance gate) — bring up the stores + a corpus + a real key,
   generate one digest, and record `docs/m7-digest-notes.md` (decisions-not-links? weak-signals =
   cross-publisher convergence? honest noise count?). Then merge `feat/m7-feedback-digest`.
2. **M7.5 — post generator (LinkedIn + Medium).** Project the weekly intelligence (Weak Signal of
   the Week + Noise Report) into human-approved drafts; draft-only, no auto-posting.
