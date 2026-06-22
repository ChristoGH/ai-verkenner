# AI Verkenner — Project State

> **Living status doc — the single "where are we" source.** Update the date + the moving parts at
> each review gate. For the *roadmap* (what each milestone delivers) see
> [`PHASE_1_PLAN.md`](PHASE_1_PLAN.md); this file is the *current state* only.

**Last updated:** 2026-06-22

## One-line status

Phase 1 ("viable first phase") is ~75% through the milestone ladder. The pipeline runs end to end
on real data; the cross-publisher convergence signal — the project's reason to exist — is
validated. Next substantive milestone: **M7 (feedback + GraphRAG digest)**.

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
| M6.5 Source breadth (GitHub intel + recency cap) | ✅ done, **awaiting merge** | `7a6fb9f` |
| M7 Feedback + GraphRAG digest | ⏳ next | — |
| M7.5 Post generator (LinkedIn/Medium) | ⬜ pending | — |
| M8 Hardening / "viable" gate | ⬜ pending | — |
| M8.5 Read-only MCP server | ⬜ pending | — |

## Git / publish state

- **Branch:** `feat/m6.5-source-breadth` (M6.5, not yet merged to `main`).
- **`main`:** at the M5.5 tip; **2 commits ahead of `origin/main`** (M6 + M5.5 unpushed).
- **To consolidate:** merge M6.5 → `main` (fast-forward), then `git push origin main` (publishes
  M6 + M5.5 + M6.5). Push must run from Christo's machine (credentials are local).
- ~127 backend tests + 9 frontend tests passing.

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

- **Decouple `github_advisories` from the general recency cap** — Early Warning shouldn't expire in
  7 days (M6.5 finding).
- **Star-velocity is seeded but unobserved** — needs a second run to emit deltas.
- **`USER_CONTEXT` is generic** — could be seeded from the Obsidian vault (modest near-term value;
  see the vault assessment) — pragmatic v1 is a hand-written context paragraph.
- **Cost:** ~$15 of Opus per ~120-event run, roughly linear in events.

## Next step (recommended)

1. **Consolidate:** merge M6.5 → `main`, push `main`. (Drains the stacked-branch backlog.)
2. **M7 — feedback + GraphRAG digest.** The convergence signal is now good enough to build the
   first real published-output-adjacent deliverable on.
