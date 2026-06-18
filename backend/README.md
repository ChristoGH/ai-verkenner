# AI Verkenner — Backend

FastAPI backend for AI Verkenner. At the scaffold milestone (Task 001) it serves a health check
and registers placeholder modules. The canonical scoring rule (`app/scoring/priority.py`) is real
and tested, but deliberately not wired into any pipeline yet.

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
- Interactive docs (titled *AI Verkenner API*): <http://localhost:8000/docs>

## Test

```bash
pytest
```

`test_health.py` checks the health endpoint; `test_priority.py` covers the canonical
priority-class rule (including the `(5, 0) → immediate_priority` regression).

## Layout

```
app/
├── main.py        FastAPI app + CORS; includes the health router
├── core/          config (resolves PROMPTS_DIR, SOURCES_FILE against the repo root)
├── api/           routers (health implemented; others stubbed)
├── db/            SQLite layer (placeholder — Task 004)
├── models/        entities (placeholder — Task 004+)
├── ingestion/     source fetching (placeholder — Task 003)
├── enrichment/    LLM enrichment (placeholder — Task 005; imports scoring/priority.py)
├── scoring/       priority.py (canonical, tested) + scales constants
└── digests/       digest generation (placeholder — Task 008)
```
