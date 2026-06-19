# AI Verkenner — Backend

FastAPI backend for AI Verkenner. At milestone **M1** (Tasks 002 + 003) it serves a health check,
exposes the curated source registry (`GET /sources`), and runs fail-safe-per-source ingestion of
RSS / GitHub-releases / arXiv into in-memory `RawItem`s. The canonical scoring rule
(`app/scoring/priority.py`) is real and tested; storage, enrichment, and the graph/vector stores
arrive in later milestones (M2+).

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
- Health: <http://localhost:8000/health> →
  `{"status":"ok","service":"ai-verkenner","version":"0.1.0"}`
- Sources: <http://localhost:8000/sources> (filter with `?enabled=true|false`)
- Interactive docs (titled *AI Verkenner API*): <http://localhost:8000/docs>

The source registry is read from `SOURCES_FILE` (default `sources/sources.yaml`, resolved at the
repo root). A malformed entry is reported (logged) and skipped — it never crashes a request or a
run. Ingestion (`app.ingestion.run_ingestion`) is a library call at M1, not yet an endpoint.

## Test

```bash
pytest
```

`test_health.py` and `test_priority.py` cover the scaffold (priority regression `(5,0) →
immediate_priority`). `test_sources_registry.py` / `test_sources_api.py` cover registry validation
and `GET /sources`; `test_ingestion.py` covers the RSS/GitHub/arXiv parsers, the arXiv URL builder,
the GitHub-intelligence stubs, and per-source failure isolation in the orchestrator.

## Layout

```
app/
├── main.py        FastAPI app + CORS; includes health + sources routers
├── core/          config (PROMPTS_DIR, SOURCES_FILE, HTTP timeout/user-agent)
├── api/           routers (health, sources)
├── schemas/       Pydantic shapes — Source, SourceType, TrustLevel, RawItem (M1)
├── sources/       registry loader (validate sources.yaml, fail-safe)
├── ingestion/     orchestrator + fetchers/ (rss, github_releases, arxiv; github_* stubs → M3)
├── db/            SQLite layer (placeholder — Task 004 / M3)
├── models/        SQLModel persistence entities (placeholder — Task 004 / M3)
├── enrichment/    LLM enrichment (placeholder — Task 005 / M4; imports scoring/priority.py)
├── scoring/       priority.py (canonical, tested) + scales constants
└── digests/       digest generation (placeholder — Task 008 / M7)
```
