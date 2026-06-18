# AI Verkenner

**AI Verkenner** ("AI Scout") is a personal AI intelligence and early-warning system. It
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

This repository is at the **scaffold milestone (Task 001)**. The backend serves a health
check, the frontend renders a shell that polls it, and the full project documentation, task
plan, prompt templates, and curated source registry are in place. There is **no ingestion, no
LLM enrichment, and no real database yet** — those arrive in later tasks (see
[`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)).

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
