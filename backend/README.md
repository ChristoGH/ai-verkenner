# AI Verkenner — Backend

FastAPI backend for AI Verkenner. At milestone **M5** it serves health/readiness checks, the curated
source registry (M1), fail-safe ingestion (M1), SQLite persistence + embeddings + semantic dedup
(M3), cloud-LLM enrichment + entity/relationship extraction (M4), and — new in M5 — **projects the
SQLite graph (items/sources/entities/events/topics + timestamped edges) into Neo4j** with idempotent
MERGEs, plus a **graph-aware ranking signal** (convergence across distinct sources + centrality +
recency). The graph signal is layered ON TOP OF the canonical priority class
(`app/scoring/priority.py`, imported, never re-derived): it reorders within/across classes but never
changes the class, and **hype still only demotes**. Projection is **degrade-don't-crash** (a Neo4j
write failure leaves the Event flagged for re-projection and the run continues); `graph-reindex`
rebuilds Neo4j purely from SQLite. SQLite is the source of truth; Qdrant and Neo4j are rebuildable
derived indices (ADR 0001).

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
no API key, no live containers**. M1–M4 suites as before; new in M5: `test_graph_projection.py`
(expected nodes/edges, idempotent re-projection, `graph_reindex` rebuild-matches-from-SQLite, SQLite
survives a simulated Neo4j write failure) and `test_graph_signals.py` (convergence promotes within a
class without changing the class; hype still demotes; the signal never crosses priority classes).

## Layout

```
app/
├── main.py        FastAPI app + CORS + lifespan (closes store clients on shutdown)
├── cli.py         run [--no-enrich|--no-graph] · reindex (Qdrant) · graph-reindex (Neo4j)
├── core/          config (paths, store URLs, embedder, DEDUP_TAU, LLM_*, GRAPH_* weights)
├── api/           routers (health + /health/ready, sources)
├── schemas/       Pydantic shapes — ingestion (Source, RawItem) + enrichment (scores, entities)
├── sources/       registry loader (validate sources.yaml, fail-safe)
├── ingestion/     orchestrator + fetchers/ (rss, github_releases, arxiv; github_* stubs)
├── embeddings/    Embedder interface · HashingEmbedder (deterministic) · sentence-transformers
├── enrichment/    provider (LLM, lazy) · prompts · parse · fallback · graph_store · enricher
├── graph/         GraphStore (Neo4j + in-memory) · projection (project_new/reindex) · util/schema
├── db/            store clients — qdrant.py, neo4j.py (ping), sqlite.py, qdrant_index.py
├── models/        SQLModel tables — Source/RawItem/Event/EnrichedItem/Entity/Relationship
├── storage/       hashing · repository (persist) · dedup (events + reindex) · pipeline (run path)
├── scoring/       priority.py (canonical) · scales · ranking (hype-aware) · graph_signals (M5)
└── digests/       digest generation (placeholder — Task 008 / M7)
```
