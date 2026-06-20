# AI Verkenner — Backend

FastAPI backend for AI Verkenner. Through M5 it ingests (M1), persists + embeds + de-duplicates
(M3), enriches with a cloud LLM + extracts entities/relationships (M4), and projects into a Neo4j
graph with a graph-aware ranking signal (M5). New in **M6** is the **dashboard surface**:

- `GET /items` — ranked **Core Radar**: `rank_with_graph` (priority class first, then hype-aware
  salience + graph signal). Filter by `priority_class` and by mentioned `entity`. Each item carries
  its source link, the five scores (hype labelled inverted), summary (fact) vs why/action
  (interpretation), and the graph signal's `why`.
- `GET /graph` — the **Cosmograph** projection: capped `{nodes, links}` (events + top entities by
  degree), filterable by `window_days`/`priority`. `available: false` when Neo4j is down.
- `GET /horizon` — the **weak-signal** view: the `horizon_signal`/`archive` quadrant ranked by graph
  **convergence** (NOT the Core Radar order), each with its `why` + contributing sources.

The graph signal is layered ON TOP OF the canonical priority class (`app/scoring/priority.py`,
imported, never re-derived) — it reorders, never changes the class, and **hype still only demotes**.
Every dashboard endpoint **degrades cleanly** when Neo4j is down (graph-less ordering, empty graph).
SQLite is the source of truth; Qdrant and Neo4j are rebuildable derived indices (ADR 0001).

## Requirements

- Python 3.11+

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[test]"
# For real local embeddings (downloads a model; otherwise set EMBEDDER=hashing):
pip install -e ".[embeddings]"
# For the real cloud LLM enrichment (otherwise runs use the rule-based fallback):
pip install -e ".[llm]"
```

## Run

```bash
uvicorn app.main:app --reload
```

- API: <http://localhost:8000>
- Health (liveness): <http://localhost:8000/health> →
  `{"status":"ok",...,"dependencies":{"qdrant":"ok|unreachable","neo4j":"ok|unreachable"}}`
- Readiness: <http://localhost:8000/health/ready> → `200` when every store is reachable, else `503`
- Sources: <http://localhost:8000/sources> (filter with `?enabled=true|false`)
- Interactive docs (titled *AI Verkenner API*): <http://localhost:8000/docs>

The backend reaches the derived stores via `QDRANT_URL` / `NEO4J_URI` / `NEO4J_USER` /
`NEO4J_PASSWORD` (see `.env.example`); defaults target `docker compose up qdrant neo4j` on the host.
A store being down **never crashes the app** — `/health` stays `200` and marks it `unreachable`.
Start the stores with `docker compose up qdrant neo4j` (from the repo root), or the whole stack with
`docker compose up --build`. RAM: budget ~2 GB for the two stores, ~3 GB for the full stack.

The source registry is read from `SOURCES_FILE` (default `sources/sources.yaml`, resolved at the
repo root). A malformed entry is reported (logged) and skipped — it never crashes a request or a
run. Ingestion (`app.ingestion.run_ingestion`) is a library call, not yet an endpoint.

### Store + enrich + graph CLI

```bash
# Ingest → SQLite + Qdrant → dedup → enrich (M4) → project to Neo4j (M5):
python -m app.cli run
python -m app.cli run --no-enrich   # skip enrichment (M3 behaviour)
python -m app.cli run --no-graph    # skip the Neo4j projection (M4 behaviour)
# Rebuild a derived index purely from SQLite (proves the derived-index invariant):
python -m app.cli reindex           # Qdrant 'items' collection
python -m app.cli graph-reindex     # Neo4j knowledge graph
```

`run` honours `DATABASE_URL`, `QDRANT_URL`, `NEO4J_*`, the embedder selector, and the LLM provider.
Dedup is two-stage (content hash → Qdrant ANN ≥ `DEDUP_TAU`) and idempotent; enrichment runs once
per new Event; **graph projection runs after enrichment**, is idempotent (MERGE), and degrades if
Neo4j is down (the Event is flagged `projected=False` for a later `graph-reindex`).

## Test

```bash
pytest
```

All tests are **offline and deterministic**: in-memory SQLite, in-process Qdrant (`:memory:`), a
`HashingEmbedder`, a **fake LLM provider**, and an **in-memory graph store** — **no model download,
no API key, no live containers**. M1–M5 suites as before; new in M6: `test_dashboard_api.py`
(`/items` ranked; `/horizon` returns only the weak-signal quadrant ranked by convergence with the
operational item excluded and the converging one on top; `/graph` capped nodes/links; all three
degrade when Neo4j is down) and `test_qdrant_index.py` (the dim-mismatch self-heal from the M6 smoke).
Frontend tests run with `npm test` (vitest). A real-data smoke is in `docs/m6-smoke-notes.md`.

## Layout

```
app/
├── main.py        FastAPI app + CORS + lifespan (closes store clients on shutdown)
├── cli.py         run [--no-enrich|--no-graph] · reindex (Qdrant) · graph-reindex (Neo4j)
├── core/          config (paths, store URLs, embedder, DEDUP_TAU, LLM_*, GRAPH_* weights)
├── api/           routers (health, sources, items, graph, horizon) · deps · dashboard_service
├── schemas/       Pydantic shapes — ingestion · enrichment · api (ItemOut/GraphOut/HorizonOut)
├── sources/       registry loader (validate sources.yaml, fail-safe)
├── ingestion/     orchestrator + fetchers/ (rss, github_releases, arxiv; github_* stubs)
├── embeddings/    Embedder interface · HashingEmbedder (deterministic) · sentence-transformers
├── enrichment/    provider (LLM, lazy) · prompts · parse · fallback · graph_store · enricher
├── graph/         GraphStore (Neo4j + in-memory) · projection · graph_view (Cosmograph) · util
├── db/            store clients — qdrant.py, neo4j.py (ping), sqlite.py, qdrant_index.py
├── models/        SQLModel tables — Source/RawItem/Event/EnrichedItem/Entity/Relationship
├── storage/       hashing · repository (persist) · dedup (events + reindex) · pipeline (run path)
├── scoring/       priority.py (canonical) · scales · ranking (hype-aware) · graph_signals
└── digests/       digest generation (placeholder — Task 008 / M7)
```
