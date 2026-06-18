# Task 001 — Repo Scaffold

**Status: DONE** ✅

## Goal

Stand up a clean, runnable AI Verkenner monorepo: a backend that serves a health check, a
frontend shell that polls it, complete project documentation, all eight task files, the prompt
templates, and the curated source stub — plus the canonical, tested scoring rule. No ingestion,
no LLM calls, no real database.

## Scope

- Repo root: `README.md`, `.env.example`, `.gitignore`, commented placeholder
  `docker-compose.yml`, and the binding `CLAUDE.md` agent contract.
- `docs/` — project brief (with the verbatim scoring section and a seeded change log), PRD,
  technical design, implementation plan, and an ADR template under `docs/decisions/`.
- `tasks/` — task files 001–008.
- `prompts/` — `classify_item.md`, `summarise_item.md`, `weak_signal.md`, `digest.md`.
- `sources/sources.yaml` — ~16 curated seeds.
- `backend/` — FastAPI app with `GET /health`, placeholder modules
  (`core`, `api`, `db`, `models`, `ingestion`, `enrichment`, `scoring`, `digests`),
  the real `scoring/priority.py`, `pyproject.toml` (`name = "ai-verkenner"`), and tests.
- `frontend/` — Vite + React + TS + Tailwind + shadcn/ui shell with a health badge and five
  page stubs.

## Non-goals

- No source loading, fetching, parsing, persistence, or LLM calls.
- No real database; `db/` and `models/` are placeholders.
- `scoring/priority.py` is **pure logic only** — it is **not** wired into any pipeline (that is
  Task 005).
- No auth, Docker production, Qdrant, Redis, Postgres, Kubernetes, crawler, or browser
  automation.

## Acceptance criteria

- Backend starts (`uvicorn app.main:app`) and `GET /health` returns
  `{"status":"ok","service":"ai-verkenner","version":"0.1.0"}` with status 200.
- `/docs` shows the title **AI Verkenner API**.
- `pytest` passes: health test + `priority.py` regression test.
- Frontend `npm run dev` compiles with zero errors; the health badge polls and renders OK
  against the running backend.
- A case-insensitive search for any legacy product name (excluding `.git`/`node_modules`)
  returns **zero** hits.
- Docs, task files, prompts, and `sources.yaml` are all present and correctly named.

## Files likely to change

The whole initial tree (this task creates it). After 001, this file is not edited again.

## Test plan

- `cd backend && pytest` — `test_health.py` (200 + `status == "ok"`) and `test_priority.py`
  (the priority-class cases, including the `(5, 0) → immediate_priority` regression).
- Manual: start uvicorn, `curl /health`, open `/docs`; start the frontend, confirm the badge
  goes green.
- A case-insensitive search for any legacy product name (excluding `.git`/`node_modules`) → zero
  hits.

## Agent constraints

- Product name is **AI Verkenner** everywhere; slug `ai-verkenner`. No legacy or alternate
  product name may appear anywhere in the repo.
- Honour `CLAUDE.md`. Build nothing outside this task's scope.
- One branch (`feat/001-repo-scaffold`), one logical change set, stop at the human review gate.

## Paste-ready agent prompt

> Scaffold the AI Verkenner monorepo per `tasks/001-repo-scaffold.md` and `CLAUDE.md`. Create the
> full tree (root files, docs, tasks, prompts, sources, runnable backend with `GET /health` and a
> tested `scoring/priority.py`, runnable frontend shell with a health badge). No ingestion, no
> LLM, no real DB. Ensure `pytest` passes, the backend and frontend run, and there are zero
> references to any legacy product name. Work on `feat/001-repo-scaffold`; do not merge — stop at
> the review gate with a summary.
