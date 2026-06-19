# CLAUDE.md — Agent operating contract for AI Verkenner

This file is binding. Any agent (or human) doing work in this repository follows it.

## Project

- **Project:** AI Verkenner — a personal AI intelligence and early-warning system.
- **Canonical brief:** [`docs/AI_VERKENNER_PROJECT_BRIEF.md`](docs/AI_VERKENNER_PROJECT_BRIEF.md).
- **Decisions:** [`docs/decisions/`](docs/decisions/) (Architecture Decision Records).
- **Unit of work:** the task files in [`tasks/`](tasks/). Do not start work that no task file
  calls for.

The product name is **AI Verkenner** everywhere. The slug / package identifier is
`ai-verkenner`. There is no other name for this product.

## Core loop to protect

```
source → raw item → deduplication → enrichment → ranking → dashboard → feedback → digest
```

Every feature must serve this loop. If a proposed change does not make this loop better,
faster, more accurate, or more useful, it does not belong in the MVP.

## MVP stack (fixed — do not substitute)

- **Backend:** FastAPI · SQLite (later) · httpx · feedparser · python-dotenv ·
  SQLModel/SQLAlchemy (later) · YAML source registry.
- **Graph / vector / visual (sanctioned by [ADR 0001](docs/decisions/0001-graph-vector-visual-stack.md)):**
  Qdrant (vectors / semantic dedup) · Neo4j (knowledge graph) · Cosmograph (`@cosmograph/react`
  visualisation). Deployed locally via Docker Compose; arriving by milestone in
  [`docs/PHASE_1_PLAN.md`](docs/PHASE_1_PLAN.md) (M2+), not in the M1 ingestion slice.
- **Frontend:** React · Vite · TypeScript · Tailwind · shadcn/ui · TanStack Query · Zod.

A **read-only, local MCP surface** and the **curated GitHub-intelligence `source_type`s**
(`github_star_velocity`, `github_new_repos`, `github_advisories`, `github_changes`) are sanctioned
by [ADR 0002](docs/decisions/0002-mcp-server-and-github-intelligence.md). These stay curated (watched
list in `sources.yaml` + official GitHub API) — they are **not** a broad crawler.

## Do NOT build without a task file that explicitly calls for it

The following are deliberately out of scope. Adding any of them without a task file that names
it is a contract violation:

Postgres · Redis · Kubernetes · Docker production setup · auth / login · broad web crawler ·
browser automation · billing / payments · multi-user · Slack / Teams / email integrations ·
complex multi-agent systems · plugin framework · read/write (mutating) MCP surface.

> **Sanctioned out of this list by ADRs (do build, by milestone):** Qdrant, Neo4j, and a graph
> database — moved into the stack by [ADR 0001](docs/decisions/0001-graph-vector-visual-stack.md).
> A **read-only** local MCP surface and the curated GitHub-intelligence source types — sanctioned
> by [ADR 0002](docs/decisions/0002-mcp-server-and-github-intelligence.md). Everything else above
> stays excluded until a task file names it.

## Invariants

These hold across every feature, now and later:

- **Preserve every source URL, always.** A surfaced item without its source link is a bug.
- **Fail safely per source.** One bad source (network error, malformed feed, parse failure)
  must never break a run. Isolate failures; keep going.
- **Separate source fact from interpretation** in all outputs. Never present an inferred claim
  as if the source stated it. No unsupported claims.
- **Scoring polarity.** `relevance`, `novelty`, `actionability`, and `strategic_potential` all
  run **higher = more salient**. `hype` is **INVERTED**: `0` = strong signal, `5` = pure noise.
  Never sum `hype` additively with the others; treat it as a penalty / demotion or a filter.
- **One source of truth for the priority rule.** The canonical priority-class rule lives in
  [`backend/app/scoring/priority.py`](backend/app/scoring/priority.py). Do **not** re-derive it
  inline anywhere else — import it.
- **SQLite is the source of truth; Qdrant and Neo4j are rebuildable derived indices.** A re-index
  job must be able to reconstruct both from SQLite. A vector/graph write failure must never lose
  the SQLite record (per [ADR 0001](docs/decisions/0001-graph-vector-visual-stack.md)).

## Process

- **One slice at a time.** Implement the smallest coherent change that advances the current
  task. Don't bundle unrelated work.
- **Human review gate before merge.** Every task ends at a review gate. Do not self-merge.
- **Keep docs in sync.** When behavior or architecture changes, update the README, the relevant
  task file, and `docs/TECHNICAL_DESIGN.md` in the same change set.
- **Clear structure over clever abstractions.** No abstraction before three real use cases.
  Prefer obvious, boring code that the next reader understands immediately.
