# AI Verkenner — Backend

FastAPI backend for AI Verkenner. At milestone **M4** it serves health/readiness checks, the
curated source registry (`GET /sources`, M1), fail-safe-per-source ingestion (M1), SQLite
persistence + local embeddings + semantic dedup into `Event`s (M3), and — new in M4 — **enriches**
each new, de-duplicated Event with a cloud LLM (the five scores with hype inverted +
summary/why/action, fact separated from interpretation) and **extracts entities + timestamped
relationships** for the graph. The priority class is imported from `app/scoring/priority.py` (never
re-derived); a ranking helper treats hype as a demotion only. Graph writes go to **SQLite** at M4
(Neo4j projection is M5). SQLite is the source of truth; Qdrant is a rebuildable derived index
(ADR 0001). Enrichment is **fail-safe per item**: a missing/failed/garbled LLM call degrades to a
deterministic rule-based fallback rather than aborting the run.

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

### Store + enrich CLI

```bash
# Ingest → SQLite + Qdrant → dedup into Events → enrich the new Events (M4):
python -m app.cli run
python -m app.cli run --no-enrich   # skip enrichment (M3 behaviour)
# Rebuild the Qdrant 'items' collection purely from SQLite (proves the derived-index invariant):
python -m app.cli reindex
```

`run` honours `DATABASE_URL`, `QDRANT_URL`, the embedder selector (`EMBEDDER` / `EMBEDDING_MODEL`),
and the LLM provider (`LLM_PROVIDER` / `LLM_MODEL`). Dedup is two-stage — exact **content hash**
then **Qdrant ANN cosine ≥ `DEDUP_TAU`** (default `0.92`) — and idempotent. Enrichment runs **once
per new Event** (not per duplicate) and is idempotent too (one `EnrichedItem` per Event); with no
API key it still enriches via the rule-based fallback.

## Test

```bash
pytest
```

All tests are **offline and deterministic**: in-memory SQLite, in-process Qdrant (`:memory:`), a
`HashingEmbedder`, and a **fake LLM provider** — **no model download, no API key, no live
containers**. M1/M2/M3 suites as before; new in M4: `test_enrichment.py` (output→`EnrichedItem`
mapping, priority class from the canonical fn, malformed-output + no-provider fallback, entity
normalisation/merge, fact-vs-interpretation, idempotency), `test_enrichment_parse.py` (JSON
repair/validation), `test_ranking.py` (hype demotion, never additive).

## Layout

```
app/
├── main.py        FastAPI app + CORS + lifespan (closes store clients on shutdown)
├── cli.py         store + enrich path — `python -m app.cli run [--no-enrich] | reindex`
├── core/          config (paths, HTTP, store URLs, embedder, DEDUP_TAU, LLM_PROVIDER/MODEL, ...)
├── api/           routers (health + /health/ready, sources)
├── schemas/       Pydantic shapes — ingestion (Source, RawItem) + enrichment (scores, entities)
├── sources/       registry loader (validate sources.yaml, fail-safe)
├── ingestion/     orchestrator + fetchers/ (rss, github_releases, arxiv; github_* stubs)
├── embeddings/    Embedder interface · HashingEmbedder (deterministic) · sentence-transformers
├── enrichment/    provider (LLM, lazy) · prompts · parse · fallback · graph_store · enricher
├── db/            store clients — qdrant.py, neo4j.py (ping), sqlite.py (engine), qdrant_index.py
├── models/        SQLModel tables — Source/RawItem/Event (M3) + EnrichedItem/Entity/Relationship (M4)
├── storage/       hashing · repository (persist) · dedup (events + reindex) · pipeline (run path)
├── scoring/       priority.py (canonical, tested) · scales · ranking (hype-aware)
└── digests/       digest generation (placeholder — Task 008 / M7)
```
