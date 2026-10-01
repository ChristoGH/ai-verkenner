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
- **`backend/app/ingestion/`** — source fetching, fail-safe per source (Task 003). M6.5 adds the
  curated `github_*` fetchers (`fetchers/github_intelligence.py` — new repos / star velocity /
  advisories / changes via the official API, watched targets from `sources.yaml`, skipped without
  `GITHUB_TOKEN`), the per-source recency cap (`orchestrator.apply_recency_cap`), and honest
  star-velocity snapshots (`star_velocity_store.py` → `RepoStarSnapshot`).
- **`backend/app/enrichment/`** — M4 enrichment + extraction: a provider-abstracted LLM client
  (`provider`, cloud by default, lazily imported), `prompts` (render the `prompts/` templates),
  `parse` (JSON repair + validation), `fallback` (deterministic rule-based degrade), `graph_store`
  (basic entity resolution + relationship persistence), and `enricher` (per-Event orchestration).
  Imports `scoring/priority.compute_priority_class`; never re-derives the rule.
- **`backend/app/graph/`** — the M5 Neo4j projection: a small `GraphStore` interface with two
  implementations (`neo4j_store` real Cypher, `memory` in-memory for tests), `projection`
  (`project_event` / `project_new_events` degrade-don't-crash / `graph_reindex` rebuild-from-SQLite),
  and `util` (label/edge whitelists, entity-type → label, UTC normalisation). Idempotent MERGEs.
  **Entity normalisation (task 014):** `aliases.py` resolves curated surface forms onto one
  canonical `Entity.id` at projection time, from the human-editable `sources/entity_aliases.yaml` —
  explicit map only, no fuzzy matching or learned resolution, and an unlisted form stays its own
  entity. SQLite is never rewritten, so deleting the YAML and re-running `graph-reindex` restores
  the un-normalised graph exactly (ADR 0001). `scoring/graph_signals` resolves the event's SQLite
  entity ids through the same map, so both sides of the identity agree. Normalisation makes the
  merged concept node *larger*, which is why task 013's driver stoplist had to land first (D-026)
  and why a test pins that the canonical node stays ineligible to label a weak signal.
- **`backend/app/scoring/`** — `priority.py` (the canonical priority rule, real and tested),
  scoring scale constants, `ranking.py` (hype-aware salience + the M5 `rank_with_graph` blend), and
  `graph_signals.py` (convergence/centrality/recency, hub-dampened in M5.5 — IDF + distinct-source
  independence gate + singleton suppression). Pure logic; the graph signal adjusts order only, never
  the priority class, and hype stays a demotion.
- **`backend/app/digests/`** — digest generation (Task 008).
- **`backend/app/api/`** — routers. M6 adds the dashboard surface (`items`, `graph`, `horizon`)
  over a shared `dashboard_service` (rank/serialise/convergence) with injectable `deps` (session +
  graph store, so endpoints degrade when Neo4j is down and tests run offline).
- **`frontend/`** — the React shell (M6 wires it to the API): the Zod-validated client (`api/items`,
  `api/graph`, `api/horizon`), a real `ItemCard`, an `ItemsFeed`, the **Core Radar** + **Items**
  pages, a **Horizon** page (weak-signal quadrant with evidence), and a **Graph** page rendering
  `@cosmograph/react` (`CosmographView`, lazy-loaded) where clicking an entity filters the list.
  Tested with vitest (jsdom; Cosmograph + API mocked).

## The root-level `prompts/` and `sources/` decision

`prompts/` and `sources/` live at the **repository root**, *not* nested under `backend/`. This is
a deliberate decision (it resolves an earlier ambiguity):

- **Why root-level.** They are *content/configuration*, not application code. Prompt wording and
  the source registry are edited by a human curator and should be reviewable and diffable without
  digging into the backend package. Keeping them at the root keeps that editorial surface
  obvious, and keeps them reusable by future components (e.g. a separate job runner) without a
  backend dependency.
- **How the backend resolves them.** Paths are **configurable**, never hard-coded. `core/config`
  reads `PROMPTS_DIR` (default `prompts`), `SOURCES_FILE` (default `sources/sources.yaml`),
  `ENTITY_ALIASES_FILE` (default `sources/entity_aliases.yaml`, task 014) and `USER_CONTEXT_PATH`
  (default `docs/USER_CONTEXT.md`, task 017) from the environment and resolves them against the
  repository root (the parent of `backend/`) through **one** helper, `_resolve`. This means the
  backend has no embedded assumption about the directory layout — change the env var and the
  content can live anywhere, including a mounted volume in a future container setup. There is
  deliberately **one** resolution convention: a second one is how a document and the runtime drift
  apart without anyone noticing, which is exactly what D-069 found.

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

**`user_context` — what `relevance` is scored *against* (task 017).** `relevance` asks "is this
about *this* user's work", so the answer is bounded by the description of that work supplied on
every call. `core/config` resolves it in an explicit precedence: an explicit `USER_CONTEXT` env
value (a per-run experiment override) → the file at `USER_CONTEXT_PATH`, default
`docs/USER_CONTEXT.md` → a built-in 309-character literal. **No fall-back is silent:** a configured
file that is unreadable or empty logs a WARNING at resolution time (which reaches stderr even
before `basicConfig` runs), and `log_user_context_source()` names the source in force once at
startup from `app.cli.main` and the API lifespan. This is not defensive decoration — until task 017
the document that calls itself *"the ground truth AI Verkenner uses to score `relevance`"* was
referenced in no Python file, the literal was silently in force, and three billable calibration
runs ($4.77) tuned prompt wording against it (D-062, D-069; addendum §7).

`settings.user_context` is read by **three** surfaces, not one: the enrichment classify call
(`enrichment/enricher.py` → `prompts.render_item_inputs`), the digest **composition** call
(`digests/generator.py` → `render.render_llm_inputs`), and the digest **retrieval** step
(`digests/retrieve.py:build_theme_text`, which embeds it as the Qdrant theme query). Wiring it at
settings level therefore also changes which items a digest retrieves and how it is written, not
only how items are scored — a consequence recorded rather than absorbed (D-074).

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

**M6 dashboard (current).** The `api/` dashboard endpoints make the intelligence visible:
`GET /items` (ranked Core Radar via `rank_with_graph`, filterable by class/entity), `GET /graph`
(the `GraphStore.graph_view` Cosmograph projection — top entities by degree + the events that
mention them, capped to `limit` for legibility), and `GET /horizon` (the `horizon_signal`/`archive`
quadrant ranked by graph convergence — the query behind the "Weak Signal of the Week", with each
item's `why` + contributing sources). All three **degrade** when Neo4j is unreachable. The frontend
consumes them through Zod-validated clients and renders Core Radar, Items, Horizon, and a Cosmograph
Graph view. The first **real-data run** (live feeds + Neo4j + a cloud LLM) is documented in
[`m6-smoke-notes.md`](m6-smoke-notes.md); its headline finding — the convergence signal currently
favours *hub* entities over *quietly-emerging* ones (PHASE_1_PLAN §7) — is a Phase-2 item, and the
smoke also surfaced + fixed a Qdrant collection dimension-drift (now self-healing in
`qdrant_index.ensure_collection`).

**M5.5 convergence quality / hub-dampening (current).** The M6 smoke proved the naive
"distinct sources" convergence rewarded ubiquitous **hubs** ('GitHub', a prolific author). M5.5
re-shapes `graph_signals` to surface *quietly-emerging* entities instead, with three documented
dampeners: an **independence gate** (≥ `GRAPH_MIN_SOURCES` distinct sources, default 2 — gating the
centrality term too, so a single-feed author can't dominate), **IDF weighting**
(`idf = ln(total_developments / developments_mentioning_entity)` — ubiquitous hubs suppressed), and
**singleton suppression** (an entity in one development contributes ~0). The driving entity is the
one with the largest *dampened* contribution, and `/horizon`'s `contributing_sources` is now that
driving entity's distinct sources — so the `why` claim and the listed evidence agree (M6 finding
#3). The store's `ConvergenceStat` gained `event_count` + `source_names` to feed this; everything is
still served by the `GraphStore` (in-memory in tests). Re-validated on real data in
[`m5.5-rerun-notes.md`](m5.5-rerun-notes.md).

**M6.5 source breadth (current).** The M5.5 re-run showed the *signal* works but the *corpus* lacks
independent cross-publisher overlap to feed convergence. M6.5 widens the intake: a **per-source
recency cap** (`SOURCE_MAX_AGE_DAYS` / `SOURCE_MAX_ITEMS`, applied uniformly in the orchestrator)
bounds archive-serving feeds so a full `sources.yaml` run is affordable; the four long-stubbed
**`github_*` fetchers** are implemented as a *curated pipeline* (ADR 0002 — watched
orgs/users/topics/packages via the official API, never a crawler; `GITHUB_TOKEN` required, skipped
when absent; ~1 bounded call each, URLs preserved). **`github_star_velocity` is honest** — it
snapshots absolute stars to SQLite (`RepoStarSnapshot`) and reports the *delta* against the previous
run, seeding a baseline (emitting nothing) on first sight. `sources.yaml` is broadened with
independent reputable outlets (so the same development is covered by distinct publishers) and the
`github_*` sources are enabled. Re-validated on real data in
[`m6.5-run-notes.md`](m6.5-run-notes.md). No scoring/graph-schema change.

**M7 feedback + GraphRAG digest (current).** Closes the core loop. **Feedback** (`Feedback` model +
`POST /items/{id}/feedback`, wired to the `ItemCard` buttons) folds into ranking via
`scoring/feedback.py` as a transparent **within-class tiebreak** — `rank_with_graph` gained an
optional `feedback` term alongside the graph signal, so useful/save lift and not_useful demotes
*without* changing the canonical `priority_class` and with hype still a demotion; `ignore` removes
the item from the default feed. The latest action per Event wins. The **GraphRAG digest**
(`backend/app/digests/`) composes one decision-oriented briefing over **already-enriched** Events
(enrichment is never re-run): embed the period's themes → **Qdrant retrieve** (`retrieve.py`, focuses
the body on the user's themes) → **Neo4j expand** (`graph_signals` convergence) → ten sections
(`sections.py`, routed by the canonical priority class + source facts; reuses `rank_with_graph`, no
re-derivation) → **one composition LLM call** (`prompts/digest.md`) or the deterministic fallback
render (`render.py`). The weak-signals / research-radar sections draw from the hub-dampened
convergence quadrant; the noise count is the honest archived/high-hype total. **Cluster coherence
(task 010) + driver eligibility (task 013, current):** the weak-signal section is a group of items
sharing **one driving entity** — `sections.coherent_cluster()` groups on `GraphSignal.driver_uid`
(the normalised entity identity, never the display name) with a floor of `WEAK_CLUSTER_MIN_ITEMS`
(default 2), and records the winner as `DigestData.weak_driver`. The previous per-item
`convergence > 0` filter was a **per-item** property and collected items converging on unrelated
entities; a convergence may now be claimed only when `weak_driver` is non-empty, and the post
generator reads that one value rather than re-deriving coherence. **Selection is by quietness, not
size** (D-026): among groups clearing the floor, the winner is the driver with the lowest ambient
mention count (`GraphSignal.driver_mentions`, threaded from the same convergence read — no extra
query), because a weak signal is *corroborated but not yet loud*; "largest group" structurally
selected the corpus's loudest entity (D-024). Generic concept nodes ("AI", "LLM", "Large language
models", …) are categorically ineligible to *label* a cluster via `WEAK_DRIVER_STOPLIST` — selection
only; nothing is removed from the graph or from scoring. **Mention weight (task 016, current):** a
shared `driver_uid` proves items name the same entity but not that they are *about* it, and the
convergence read weights every mention equally — so a headline story and a one-line name-check
corroborated a cluster equally. `scoring/mention_weight.py` scores each **entity–item link** from the
item's own title and published body (1.0 named in the title · 0.8 named repeatedly · 0.6 named in the
lead · 0.2 named once in passing · 0.0 never named), and `coherent_cluster` admits a member only at
`>= CLUSTER_MEMBER_MIN_WEIGHT` (default 0.5). **Membership only** — an excluded item keeps its
scores, its graph edges, its corpus row and its place in every other section — and it is **not a
topicality gate**: an item strongly about the driver but off-topic for AI scores 1.0 and stays (that
is corpus scope, task 011). It is string matching over text the corpus already holds: no LLM call, no
embeddings, no re-enrichment. The published **"N independent sources"** is computed from the
weighted members' own publishers via `sections.cluster_sources()` — one source of truth, shared with
the post generator — rather than from the driving entity's graph-wide evidence, which includes
publishers that never covered the selected development and which weighting cannot affect.
Convergence maths, `GRAPH_MIN_SOURCES` and `priority.py` are untouched by this. It degrades to
SQLite-only when Qdrant/Neo4j are down and persists as `Digest` (`GET /digests`, `GET /digests/{id}`,
a Digests page). Generated via `python -m app.cli digest`.

## Still deferred (directional, not committed)

Gated behind the remaining `CLAUDE.md` exclusions until a task file names them: moving from SQLite
to Postgres; a proper job scheduler/queue; multi-user / auth; alerting; a read/write MCP surface.
Each would be recorded as an ADR before adoption.

## Cross-cutting invariants (enforced in design)

- **Preserve every source URL.** The URL is a first-class field on RawItem and survives into
  EnrichedItem, the dashboard, and the digest.
- **Fail safely per source.** Ingestion isolates each source so one failure cannot abort a run.
  **Isolation is not enough on its own:** a source that never yields is equally silent, so the
  registry keeps claiming coverage the corpus does not have. `models.SourceHealth` records each
  run's per-source outcome (fetched / kept / new / skipped / error, plus the consecutive
  zero-yield streak); `python -m app.cli sources --health` lists every enabled source, and a
  source yielding nothing for `SOURCE_ZERO_YIELD_WARN` consecutive runs is reported loudly in the
  run summary. Reporting only — no retries, no backoff, no circuit breaker, no auto-disable
  (task 011 / D-017, D-039). `app/ingestion/health.py` separates the four reasons a source shows
  zero — `error` · `no-items` (a URL that does not serve a feed) · `stale-window` (healthy, but
  quieter than `SOURCE_MAX_AGE_DAYS`) · `no-token` (a `github_*` source with no `GITHUB_TOKEN`,
  skipped by ADR 0002 design) — because only the first two are faults (D-040).
- **Fact vs. interpretation.** Enrichment outputs keep the source fact separate from the model's
  interpretation; the data model and prompts reflect this split.
- **Scoring polarity / hype inversion.** Encoded in `scoring/` and honoured by ranking: hype is a
  demotion, never an additive term. See the brief's canonical scoring section.
- **One priority rule.** `scoring/priority.py` is the single source of truth; enrichment imports
  it rather than re-implementing it.
- **SQLite is the source of truth; Qdrant and Neo4j are rebuildable derived indices.** A re-index
  job reconstructs both from SQLite; a vector/graph write failure must never lose the SQLite
  record (per [ADR 0001](decisions/0001-graph-vector-visual-stack.md)).
