# AI Verkenner — Implementation Plan

The system is built as eight reviewable slices, **001 → 008**, each defined by a file in
[`../tasks/`](../tasks/). The order is a dependency order: each task assumes the ones before it
are merged. **There is a human review gate between every task** — an agent completes a task on
its own branch, stops, and hands it to a human, who reviews and merges before the next task
starts. No task self-merges, and no task begins before its predecessor is merged.

## The sequence

### 001 — repo-scaffold
Stand up a clean, runnable monorepo: backend (FastAPI with a `GET /health` check and placeholder
modules), frontend (React/Vite shell with a live health badge), full documentation, all eight
task files, the prompt templates, and the curated source stub. Includes the canonical, tested
`scoring/priority.py` (not yet wired into any pipeline). No ingestion, no LLM, no real database.
*Gate: backend and frontend run, health badge is green, `pytest` passes, zero references to any
legacy product name.*

### 002 — source-registry
Load and validate `sources/sources.yaml` through `core/config` (configurable path), model a
`Source`, and expose `GET /sources`. Validation rejects malformed entries clearly. Still no
fetching. *Gate: the registry parses, invalid entries are reported, `GET /sources` returns the
configured sources.*

### 003 — rss-github-ingestion
Fetch each enabled source — RSS/Atom via `feedparser`, GitHub releases and arXiv via `httpx` —
and produce `RawItem`s in memory. **Fail safely per source**: a single bad source logs and is
skipped, never aborting the run. Every item preserves its source URL. *Gate: a run over the
registry produces raw items and survives a deliberately broken source.*

### 004 — storage-deduplication
Introduce SQLite (SQLModel/SQLAlchemy). Persist `Source` and `RawItem`, and **deduplicate** raw
items (stable hash over identifying fields) so re-runs don't create duplicates. *Gate: items
persist, a second run adds no duplicates, schema is migration-friendly.*

### 005 — llm-enrichment
Enrich each new `RawItem` into an `EnrichedItem`: classification/tags, the **five scores**
(respecting the **hype inversion**), summary, why-it-matters, connection-to-user-work, and a
recommended action. The **priority class must be computed by importing
`app/scoring/priority.py`** — it must *not* be re-implemented inline, and ranking must treat hype
as a demotion. Prompts come from `prompts/`. *Gate: enrichment produces well-formed output,
priority classes match `priority.py`, fact and interpretation stay separate.*

### 006 — react-dashboard
Build the **Core Radar** UI: the ranked feed of real `EnrichedItem` cards (title, source,
published date, priority badge, summary, why-it-matters, recommended action, scores, source
link). Wire it to `GET /items` through the typed, Zod-validated client. *Gate: the dashboard
renders real ranked items end-to-end.*

### 007 — feedback-actions
Add the feedback loop: **useful / not useful / save / ignore** via `POST /items/{id}/feedback`,
persisted as `Feedback`, and folded back into ranking. *Gate: feedback persists and observably
affects ordering.*

### 008 — weekly-digest
Generate the **decision-oriented weekly digest** (executive summary, must-know, should-read,
weak signals, research radar, tool changes, risks, opportunities, suggested experiments,
ignored/noise count), stored as a `Digest` and readable via the API/UI. *Gate: a digest
generates from real enriched items and reads as decisions, not a link list.*

## Working agreement

Each task file carries its own goal, scope, non-goals, acceptance criteria, files likely to
change, test plan, agent constraints, and a paste-ready agent prompt. The invariants in
[`../CLAUDE.md`](../CLAUDE.md) hold throughout. Keep the README, the relevant task file, and
[`TECHNICAL_DESIGN.md`](TECHNICAL_DESIGN.md) in sync with behaviour as it lands.
