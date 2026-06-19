# AI Verkenner

**AI Verkenner** is a personal AI intelligence and early-warning system. It
watches a curated set of trusted sources, enriches what it finds, and surfaces a short,
ranked, decision-oriented view of what actually matters — so you can answer, at a glance:

> *What happened, why does it matter, does it affect my work, is it a weak signal, and what
> should I do about it?*

It is built as a **curated pipeline, not a broad web crawler**. Quality of sources over
quantity of noise.

## The three modules

- **Core Radar** — the day-to-day feed: what happened across your trusted sources, deduplicated,
  enriched, and ranked by how much it matters to *you*.
- **Horizon Scanner** — weak-signal detection: things with low current relevance but high
  potential future importance (the research-radar quadrant).
- **Early Warning System** — flags developments that demand attention now: security advisories,
  breaking changes, and shifts in tools you depend on.

## Status

This repository is at milestone **M2 — Infra up** on the Phase 1 ladder
([`docs/PHASE_1_PLAN.md`](docs/PHASE_1_PLAN.md)). Done so far: the backend serves health/readiness
checks and the curated source registry (`GET /sources`), fail-safe-per-source ingestion produces
in-memory `RawItem`s (M1), and `docker compose` brings up the two derived stores —
**Qdrant** (vectors) and **Neo4j** (graph) — with the backend reporting their reachability. There
is still **no persistence, no embeddings, no LLM enrichment, and no graph writes** — those arrive
in M3+. SQLite remains the source of truth; Qdrant and Neo4j are rebuildable derived indices
([ADR 0001](docs/decisions/0001-graph-vector-visual-stack.md)).

## Repository layout

```
ai-verkenner/
├── backend/    FastAPI app (health check + placeholder modules + tested scoring rule)
├── frontend/   React + Vite + TypeScript shell with a live health badge
├── docs/       Project brief, PRD, technical design, implementation plan, ADRs
├── tasks/      The unit of work: tasks 001–008
├── prompts/    Decision-oriented LLM prompt templates (root-level, read via config)
└── sources/    Curated source registry (sources.yaml, root-level)
```

`prompts/` and `sources/` live at the **repository root** (not under `backend/`). The backend
resolves them through configurable paths (`PROMPTS_DIR`, `SOURCES_FILE`) — see
[`docs/TECHNICAL_DESIGN.md`](docs/TECHNICAL_DESIGN.md).

## Run it locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose (for the full stack / the derived stores)

### Full stack (Docker Compose)

One command brings up Qdrant, Neo4j, the backend, and the frontend:

```bash
cp .env.example .env        # adjust NEO4J_PASSWORD etc. for anything non-local
docker compose up --build
```

- Backend: <http://localhost:8000> · health: <http://localhost:8000/health>
- Frontend: <http://localhost:5173>
- Qdrant: <http://localhost:6333> · Neo4j browser: <http://localhost:7474> (Bolt on 7687)

Just the stores (e.g. to run the backend on the host): `docker compose up qdrant neo4j`.
Tear down with `docker compose down` (add `-v` to also drop the data volumes — they are rebuildable
derived indices, so this is safe).

**RAM minimums (rough):** Neo4j ~1.5 GB (with the heap/pagecache caps in `docker-compose.yml`),
Qdrant ~0.3 GB, backend ~0.2 GB, frontend ~0.3 GB — budget **~3 GB** free for the full stack, or
**~2 GB** for just the two stores.

The backend **degrades, never crashes**: if a store is down, `GET /health` still returns `200`
with that store marked `unreachable` under `dependencies`; `GET /health/ready` returns `503` until
every required store is reachable.

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload
```

The API runs at <http://localhost:8000>. Check it:

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"ai-verkenner","version":"0.1.0"}
```

Interactive docs (titled *AI Verkenner API*) are at <http://localhost:8000/docs>.

Run the tests:

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at <http://localhost:5173>. The dashboard shows a **health badge** that polls the
backend every 30 seconds and renders OK / degraded / unreachable.

## Where to read next

- [`docs/AI_VERKENNER_PROJECT_BRIEF.md`](docs/AI_VERKENNER_PROJECT_BRIEF.md) — the canonical brief.
- [`CLAUDE.md`](CLAUDE.md) — the operating contract for agents working in this repo.
- [`tasks/`](tasks/) — the build, one slice at a time, 001 → 008.
