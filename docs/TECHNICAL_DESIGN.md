# AI Verkenner — Technical Design

## Scope of this document

How AI Verkenner is built: the MVP architecture, how it grows, and the cross-cutting decisions
that shape both. This document tracks the *current* design; when architecture changes, update it
in the same change set and record direction changes as ADRs in [`decisions/`](decisions/).

## MVP architecture

A small, legible, single-machine system:

```
                 ┌─────────────────────────────────────────────┐
   Browser  ───▶ │  Frontend  (React + Vite + TS + Tailwind)   │
                 │  shadcn/ui · TanStack Query · Zod            │
                 └───────────────┬─────────────────────────────┘
                                 │  HTTP (JSON, validated by Zod)
                                 ▼
                 ┌─────────────────────────────────────────────┐
                 │  Backend  (FastAPI)                          │
                 │  api/ routers · core/ config · scoring/      │
                 └───┬─────────────────────────┬───────────────┘
                     │                          │
                     ▼                          ▼
         ┌──────────────────────┐   ┌──────────────────────────┐
         │  Jobs                │   │  Storage (SQLite)         │
         │  ingestion → enrich  │   │  Source · RawItem ·        │
         │  (httpx, feedparser, │   │  EnrichedItem · Feedback · │
         │   LLM scoring)       │   │  Digest                    │
         └──────────┬───────────┘   └──────────────────────────┘
                    │
                    ▼
            ┌───────────────┐        ┌──────────────────────────┐
            │  LLM provider │        │  Root content (config)    │
            │  (scoring,    │        │  prompts/   sources/      │
            │   summaries)  │        └──────────────────────────┘
            └───────────────┘
```

**Flow (the core loop).** A scheduled/triggered job reads the curated registry
(`sources/sources.yaml`), fetches each enabled source (RSS/Atom via `feedparser`, GitHub
releases and arXiv via `httpx`), and writes **RawItems** to SQLite — failing safely per source.
A second pass **deduplicates**, then **enriches** each new item with an LLM call driven by the
templates in `prompts/`, producing classification, the five scores, summary, why-it-matters,
connection-to-work, and a recommended action. The **priority class** is derived by the canonical
rule in `backend/app/scoring/priority.py`. The frontend reads the ranked **EnrichedItems**
(Core Radar), the user reacts (**Feedback**), and a periodic job rolls everything into a
**Digest**.

### Components

- **`backend/app/main.py`** — the FastAPI application. Title "AI Verkenner API", version
  "0.1.0", CORS allowing the local frontend, a lifespan that closes the store clients on shutdown.
  Exposes `GET /health`, `GET /health/ready`, and `GET /sources`.
- **`backend/app/core/`** — configuration. Reads environment (`python-dotenv`) including
  `PROMPTS_DIR`, `SOURCES_FILE`, and the M2 store settings (`QDRANT_URL`, `NEO4J_URI`,
  `NEO4J_USER`, `NEO4J_PASSWORD`), resolving content paths relative to the repository root.
- **`backend/app/api/`** — routers (`health` with liveness + readiness, `sources`); one router per
  resource as the surface grows.
- **`backend/app/db/`** — store clients for the derived indices (M2): `qdrant.py` and `neo4j.py`,
  each a thin lazily-created client plus a `ping()` that returns a `DependencyStatus`
  (reachable/unreachable) **without raising**. SQLite engine/session is still a placeholder until
  Task 004 / M3.
- **`backend/app/models/`** — SQLModel/SQLAlchemy entities (placeholder until Task 004).
- **`backend/app/ingestion/`** — source fetching, fail-safe per source (Task 003).
- **`backend/app/enrichment/`** — LLM enrichment; imports `scoring/priority.py` (Task 005).
- **`backend/app/scoring/`** — `priority.py` (the canonical priority rule, already real and
  tested) and scoring scale constants. Pure logic, no I/O, no pipeline wiring.
- **`backend/app/digests/`** — digest generation (Task 008).
- **`frontend/`** — the React shell: typed API client + Zod schemas, a polling health badge,
  and pages for Dashboard, Items, Sources, Digests, Settings.

## The root-level `prompts/` and `sources/` decision

`prompts/` and `sources/` live at the **repository root**, *not* nested under `backend/`. This is
a deliberate decision (it resolves an earlier ambiguity):

- **Why root-level.** They are *content/configuration*, not application code. Prompt wording and
  the source registry are edited by a human curator and should be reviewable and diffable without
  digging into the backend package. Keeping them at the root keeps that editorial surface
  obvious, and keeps them reusable by future components (e.g. a separate job runner) without a
  backend dependency.
- **How the backend resolves them.** Paths are **configurable**, never hard-coded. `core/config`
  reads `PROMPTS_DIR` (default `prompts`) and `SOURCES_FILE` (default `sources/sources.yaml`)
  from the environment and resolves them against the repository root (the parent of `backend/`).
  This means the backend has no embedded assumption about the directory layout — change the env
  var and the content can live anywhere, including a mounted volume in a future container setup.

## Phase 1 architecture (committed — graph / vector / visual)

[ADR 0001](decisions/0001-graph-vector-visual-stack.md) promotes the graph/vector/visual stack
from "directional" to **committed Phase-1 architecture**, operationalised by the milestone ladder
in [`PHASE_1_PLAN.md`](PHASE_1_PLAN.md). The MVP system above is the M0–M1 footprint; from **M2**
onward it grows three locally-run stores around the same core loop:

- **Qdrant** (vectors) — item-summary embeddings (local `sentence-transformers`) for two-stage
  semantic dedup / event clustering, GraphRAG retrieval, and the Cosmograph embedding projection.
- **Neo4j** (knowledge graph) — `Item`/`Source`/`Entity`/`Event`/`Topic` nodes with timestamped
  edges; the substrate for convergence / weak-signal detection and graph-expansion retrieval.
- **Cosmograph** (`@cosmograph/react`) — GPU/WebGL visualisation of the graph and embedding space,
  with Timeline / Search, fed by a backend `/graph` endpoint.

Inference is **hybrid**: a cloud LLM for enrichment and entity/relationship extraction, local
`sentence-transformers` for embeddings. All services run locally via the
`docker-compose.yml` (`qdrant`, `neo4j`, `backend`, `frontend`). The curated GitHub-intelligence
source types and a **read-only** local MCP surface are sanctioned by
[ADR 0002](decisions/0002-mcp-server-and-github-intelligence.md).

**Where it lands in the build:** M2 stands up the infra; M3 adds storage + embeddings + dedup;
M4 enrichment + extraction; M5 graph write + graph-aware ranking; M6 the Cosmograph dashboard;
M7 GraphRAG digest; M7.5/M8.5 the post generator and read-only MCP server. None of this is in the
**M1** ingestion slice (no Qdrant/Neo4j/LLM/DB yet).

**M2 connectivity & degrade model (current).** `docker compose up` runs `qdrant`, `neo4j`,
`backend`, and `frontend`; named volumes hold the store data and are disposable (rebuildable from
SQLite). The backend connects lazily through `app/db/qdrant.py` and `app/db/neo4j.py`. `GET /health`
is **liveness** — always `200` while the process runs — and additionally reports each store as
`ok` / `unreachable` under `dependencies`; a store outage degrades the report but never 5xx's the
endpoint. `GET /health/ready` is **readiness** — `503` until every required store is reachable. No
schemas, collections, or writes exist yet (M3+).

## Still deferred (directional, not committed)

Gated behind the remaining `CLAUDE.md` exclusions until a task file names them: moving from SQLite
to Postgres; a proper job scheduler/queue; multi-user / auth; alerting; a read/write MCP surface.
Each would be recorded as an ADR before adoption.

## Cross-cutting invariants (enforced in design)

- **Preserve every source URL.** The URL is a first-class field on RawItem and survives into
  EnrichedItem, the dashboard, and the digest.
- **Fail safely per source.** Ingestion isolates each source so one failure cannot abort a run.
- **Fact vs. interpretation.** Enrichment outputs keep the source fact separate from the model's
  interpretation; the data model and prompts reflect this split.
- **Scoring polarity / hype inversion.** Encoded in `scoring/` and honoured by ranking: hype is a
  demotion, never an additive term. See the brief's canonical scoring section.
- **One priority rule.** `scoring/priority.py` is the single source of truth; enrichment imports
  it rather than re-implementing it.
- **SQLite is the source of truth; Qdrant and Neo4j are rebuildable derived indices.** A re-index
  job reconstructs both from SQLite; a vector/graph write failure must never lose the SQLite
  record (per [ADR 0001](decisions/0001-graph-vector-visual-stack.md)).
