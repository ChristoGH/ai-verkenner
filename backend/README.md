# AI Verkenner — Backend

FastAPI backend for AI Verkenner. At milestone **M3** it serves health/readiness checks, the
curated source registry (`GET /sources`, M1), fail-safe-per-source ingestion of RSS /
GitHub-releases / arXiv (M1), and — new in M3 — **persists items to SQLite** (the system of record),
**embeds** them with a local model into the **Qdrant `items`** collection, and **de-duplicates**
near-identical coverage into `Event`s. The canonical scoring rule (`app/scoring/priority.py`) is
real and tested (untouched here). Enrichment and graph writes arrive in M4/M5. SQLite is the source
of truth; Qdrant is a rebuildable derived index (ADR 0001) — a Qdrant write failure never loses a
SQLite record, and dedup degrades to hash-only when Qdrant is down.

## Requirements

- Python 3.11+

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[test]"
# For real local embeddings (downloads a model; otherwise set EMBEDDER=hashing):
pip install -e ".[embeddings]"
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

### Store path CLI (M3)

```bash
# Ingest enabled sources → SQLite + Qdrant, dedup near-dups into Events:
python -m app.cli run
# Rebuild the Qdrant 'items' collection purely from SQLite (proves the derived-index invariant):
python -m app.cli reindex
```

Both honour `DATABASE_URL`, `QDRANT_URL`, and the embedder selector (`EMBEDDER` /
`EMBEDDING_MODEL`). Dedup uses a two-stage strategy — exact **content hash** then **Qdrant ANN
cosine ≥ `DEDUP_TAU`** (default `0.92`) — and is idempotent: re-runs add no duplicate rows and keep
Event assignment stable.

## Test

```bash
pytest
```

All tests are **offline and deterministic**: in-memory SQLite, in-process Qdrant (`:memory:`), and a
`HashingEmbedder` — **no model download, no live containers**. `test_priority.py` covers the
priority regression. `test_health.py` / `test_db_clients.py` cover the M2 health/readiness contract.
`test_sources_*` / `test_ingestion.py` cover M1. New in M3: `test_hashing.py` (dedup-hash stability),
`test_storage_repository.py` (idempotent persistence), `test_storage_dedup.py` (ANN grouping with no
false-merge, hash-only degrade, Qdrant-write-failure survival, reindex), `test_storage_pipeline.py`
(end-to-end run path).

## Layout

```
app/
├── main.py        FastAPI app + CORS + lifespan (closes store clients on shutdown)
├── cli.py         M3 store path — `python -m app.cli run | reindex`
├── core/          config (paths, HTTP, store URLs, EMBEDDER/EMBEDDING_MODEL/DEDUP_TAU)
├── api/           routers (health + /health/ready, sources)
├── schemas/       Pydantic ingestion shapes — Source, SourceType, TrustLevel, RawItem (M1)
├── sources/       registry loader (validate sources.yaml, fail-safe)
├── ingestion/     orchestrator + fetchers/ (rss, github_releases, arxiv; github_* stubs)
├── embeddings/    Embedder interface · HashingEmbedder (deterministic) · sentence-transformers
├── db/            store clients — qdrant.py, neo4j.py (ping), sqlite.py (engine), qdrant_index.py
├── models/        SQLModel tables — Source, RawItem, Event (the SQLite system of record)
├── storage/       hashing · repository (persist) · dedup (events + reindex) · pipeline (run path)
├── enrichment/    LLM enrichment (placeholder — Task 005 / M4; imports scoring/priority.py)
├── scoring/       priority.py (canonical, tested) + scales constants
└── digests/       digest generation (placeholder — Task 008 / M7)
```
