# AI Verkenner — Backend

FastAPI backend for AI Verkenner. At milestone **M2** it serves health/readiness checks (with
per-store reachability), exposes the curated source registry (`GET /sources`, M1), runs
fail-safe-per-source ingestion of RSS / GitHub-releases / arXiv into in-memory `RawItem`s (M1), and
carries thin clients for the two derived stores — **Qdrant** and **Neo4j** — brought up via
`docker compose`. The canonical scoring rule (`app/scoring/priority.py`) is real and tested.
Persistence, embeddings, enrichment, and graph writes arrive in M3+. SQLite is the source of truth;
Qdrant and Neo4j are rebuildable derived indices (ADR 0001).

## Requirements

- Python 3.11+

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[test]"
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

## Test

```bash
pytest
```

`test_priority.py` covers the priority regression `(5,0) → immediate_priority`. `test_health.py`
covers the M2 health/readiness contract (200-when-up, 200-but-degraded-when-down, `/ready` 503) and
`test_db_clients.py` proves each store `ping()` reports reachability without raising — all with the
clients patched, so **no live containers are needed**. `test_sources_registry.py` /
`test_sources_api.py` / `test_ingestion.py` cover the M1 registry and ingestion.

## Layout

```
app/
├── main.py        FastAPI app + CORS + lifespan (closes store clients on shutdown)
├── core/          config (PROMPTS_DIR, SOURCES_FILE, HTTP, QDRANT_URL/NEO4J_* store settings)
├── api/           routers (health + /health/ready, sources)
├── schemas/       Pydantic shapes — Source, SourceType, TrustLevel, RawItem (M1)
├── sources/       registry loader (validate sources.yaml, fail-safe)
├── ingestion/     orchestrator + fetchers/ (rss, github_releases, arxiv; github_* stubs → M3)
├── db/            store clients — qdrant.py, neo4j.py (ping = degrade-don't-crash); DependencyStatus
│                  (SQLite/SQLModel persistence still a placeholder — Task 004 / M3)
├── models/        SQLModel persistence entities (placeholder — Task 004 / M3)
├── enrichment/    LLM enrichment (placeholder — Task 005 / M4; imports scoring/priority.py)
├── scoring/       priority.py (canonical, tested) + scales constants
└── digests/       digest generation (placeholder — Task 008 / M7)
```
