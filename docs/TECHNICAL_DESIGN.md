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
- **`backend/app/db/`** — store access. `qdrant.py` and `neo4j.py` are thin lazily-created clients
  with a `ping()` returning a `DependencyStatus` **without raising** (M2). `sqlite.py` builds the
  SQLModel engine/session (M3). `qdrant_index.py` wraps the `items` collection (ensure / upsert /
  ANN search / recreate); unlike `ping`, it raises so the persistence path can catch + degrade.
- **`backend/app/models/`** — SQLModel tables (the SQLite system of record). M3: `Source`,
  `RawItem` (URL verbatim, identity `dedup_key` UNIQUE → idempotency, `content_hash`, nullable
  `event_id`, `embedded`), `Event`. M4: `EnrichedItem` (one per Event, UNIQUE; the five scores,
  fact/interpretation fields, derived `priority_class`; M5 adds a `projected` flag — the Neo4j
  analogue of `embedded`), `Entity` (`normalised_name`+`type` resolution key), `Relationship`
  (timestamped triple).
- **`backend/app/embeddings/`** — an injectable `Embedder` interface (M3): a deterministic
  `HashingEmbedder` (no model download — used by tests and as fallback) and a lazily-imported local
  `SentenceTransformerEmbedder`.
- **`backend/app/storage/`** — the M3 store path: `hashing` (the two hashes), `repository`
  (upsert sources, idempotent item persistence), `dedup` (two-stage dedup → `Event`s, and
  `reindex`), and `pipeline` (`ingest_and_store`). Driven by `app/cli.py` (`run` / `reindex`).
- **`backend/app/ingestion/`** — source fetching, fail-safe per source (Task 003).
- **`backend/app/enrichment/`** — M4 enrichment + extraction: a provider-abstracted LLM client
  (`provider`, cloud by default, lazily imported), `prompts` (render the `prompts/` templates),
  `parse` (JSON repair + validation), `fallback` (deterministic rule-based degrade), `graph_store`
  (basic entity resolution + relationship persistence), and `enricher` (per-Event orchestration).
  Imports `scoring/priority.compute_priority_class`; never re-derives the rule.
- **`backend/app/graph/`** — the M5 Neo4j projection: a small `GraphStore` interface with two
  implementations (`neo4j_store` real Cypher, `memory` in-memory for tests), `projection`
  (`project_event` / `project_new_events` degrade-don't-crash / `graph_reindex` rebuild-from-SQLite),
  and `util` (label/edge whitelists, entity-type → label, UTC normalisation). Idempotent MERGEs.
- **`backend/app/scoring/`** — `priority.py` (the canonical priority rule, real and tested),
  scoring scale constants, `ranking.py` (hype-aware salience + the M5 `rank_with_graph` blend), and
  `graph_signals.py` (M5 — convergence/centrality/recency read from the graph). Pure logic; the
  graph signal adjusts order only, never the priority class, and hype stays a demotion.
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

**M3 storage, embeddings & dedup (current).** The run path (`app/storage/pipeline.py`, exposed as
`python -m app.cli run`) is: ingest (M1, fail-safe per source) → **upsert Sources + persist new
RawItems to SQLite first** → embed each new item with the local model and **two-stage dedup** into
`Event`s — (a) exact content hash, then (b) Qdrant ANN cosine ≥ `DEDUP_TAU` — writing vectors to the
Qdrant `items` collection with payload `{item_id, source, published_at}`. The ordering encodes the
ADR-0001 invariant: **a Qdrant failure can only cost the derived index, never a record** — on a
vector write failure the item stays in SQLite, `embedded=False`, and dedup falls back to hash-only.
Re-runs are idempotent (the `dedup_key` UNIQUE constraint blocks duplicate rows; existing Event
assignments don't move). `python -m app.cli reindex` rebuilds the Qdrant collection purely from
SQLite, demonstrating the derived-index is disposable. Embeddings are **local** (sentence-
transformers; tests use a deterministic hashing embedder).

**M4 enrichment & extraction (current).** After dedup, the run path enriches **only the new
Events** (`enrich_new_events`) — the cloud LLM is called once per real-world development, not per
duplicate. For each Event's representative item the provider runs the `prompts/` templates
(`classify_item`, `summarise_item`, `weak_signal`, and the new `extract_graph`) to produce the
**five scores** (hype inverted), the human-facing fields with **fact (`summary`) separated from
interpretation** (`why_it_matters` / `connection_to_user_work` / `recommended_action`), and a
structured **entity + timestamped-relationship** payload. The `priority_class` is computed **only**
by `compute_priority_class` (imported); a `scoring/ranking.py` helper orders by priority class then
hype-demoted salience (hype subtracted, never summed). Inference is **hybrid** — cloud LLM for
enrichment, the M3 local embedder reused. **Fail-safe per item:** a missing/failed/garbled LLM call
degrades to a deterministic rule-based fallback (`method="fallback"`), so a run never stalls.
**Idempotent:** one `EnrichedItem` per Event (UNIQUE) means re-runs don't re-enrich or duplicate
entities/relationships. Entity resolution is Phase-1 **exact + normalised string match** only.

**M5 graph write & graph-aware ranking (current).** After enrichment, the run path projects the new,
enriched Events into Neo4j (`project_new_events`). The graph schema is PHASE_1_PLAN §3: `Item`,
`Source`, `Entity` (with `:Org`/`:Model`/… labels), `Event`, `Topic` nodes; `FROM`, `IN_EVENT`,
`MENTIONS {ts}`, `INTERACTS_WITH {ts, kind}`, `ABOUT` edges (`SIMILAR_TO` deferred — no persisted
pairwise scores). Every write is a `MERGE` so projection is idempotent. It is **degrade-don't-crash**
like the Qdrant path: SQLite is written first (M3/M4); a Neo4j failure is caught, the Event is left
`projected=False` for a later retry, and the run continues. `graph_reindex` clears and rebuilds the
graph purely from SQLite (the derived-index invariant). Timestamps are treated as UTC consistently
(M4 stores naive-UTC). **Graph-aware ranking** (`scoring/graph_signals.py` + `ranking.rank_with_graph`)
reads a **convergence** signal — the count of *distinct sources* touching the same entity within a
window (SIGNATURE_OUTPUTS §1) — plus degree/centrality and recency, blends them into the hype-aware
salience tiebreak, and surfaces a `why`. This reorders items **within/across priority classes only**:
the class still comes from `compute_priority_class`, and hype is never lifted. The convergence read
is served by the `GraphStore` (in-memory in tests), so ranking needs no live Neo4j to test.

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
