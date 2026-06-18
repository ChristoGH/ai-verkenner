# AI Verkenner — Technical Design

## Scope of this document

How AI Verkenner is built: the MVP architecture, how it grows, and the cross-cutting decisions
that shape both. This document tracks the *current* design; when architecture changes, update it
in the same change set and record direction changes as ADRs in [`decisions/`](decisions/).

## MVP architecture

A small, legible, single-machine system:

```
                 ┌─────────────────────────────────────────────┐
   Browser  ───▶ │  Frontend  (React + Vite + TS + Tailwind)   │
                 │  shadcn/ui · TanStack Query · Zod            │
                 └───────────────┬─────────────────────────────┘
                                 │  HTTP (JSON, validated by Zod)
                                 ▼
                 ┌─────────────────────────────────────────────┐
                 │  Backend  (FastAPI)                          │
                 │  api/ routers · core/ config · scoring/      │
                 └───┬─────────────────────────┬───────────────┘
                     │                          │
                     ▼                          ▼
         ┌──────────────────────┐   ┌──────────────────────────┐
         │  Jobs                │   │  Storage (SQLite)         │
         │  ingestion → enrich  │   │  Source · RawItem ·        │
         │  (httpx, feedparser, │   │  EnrichedItem · Feedback · │
         │   LLM scoring)       │   │  Digest                    │
         └──────────┬───────────┘   └──────────────────────────┘
                    │
                    ▼
            ┌───────────────┐        ┌──────────────────────────┐
            │  LLM provider │        │  Root content (config)    │
            │  (scoring,    │        │  prompts/   sources/      │
            │   summaries)  │        └──────────────────────────┘
            └───────────────┘
```

**Flow (the core loop).** A scheduled/triggered job reads the curated registry
(`sources/sources.yaml`), fetches each enabled source (RSS/Atom via `feedparser`, GitHub
releases and arXiv via `httpx`), and writes **RawItems** to SQLite — failing safely per source.
A second pass **deduplicates**, then **enriches** each new item with an LLM call driven by the
templates in `prompts/`, producing classification, the five scores, summary, why-it-matters,
connection-to-work, and a recommended action. The **priority class** is derived by the canonical
rule in `backend/app/scoring/priority.py`. The frontend reads the ranked **EnrichedItems**
(Core Radar), the user reacts (**Feedback**), and a periodic job rolls everything into a
**Digest**.

### Components

- **`backend/app/main.py`** — the FastAPI application. Title "AI Verkenner API", version
  "0.1.0", CORS allowing the local frontend. Currently exposes `GET /health`.
- **`backend/app/core/`** — configuration. Reads environment (`python-dotenv`) including
  `PROMPTS_DIR` and `SOURCES_FILE`, and resolves them relative to the repository root.
- **`backend/app/api/`** — router stubs; one router per resource as the surface grows.
- **`backend/app/db/`** — SQLite engine/session (placeholder until Task 004).
- **`backend/app/models/`** — SQLModel/SQLAlchemy entities (placeholder until Task 004).
- **`backend/app/ingestion/`** — source fetching, fail-safe per source (Task 003).
- **`backend/app/enrichment/`** — LLM enrichment; imports `scoring/priority.py` (Task 005).
- **`backend/app/scoring/`** — `priority.py` (the canonical priority rule, already real and
  tested) and scoring scale constants. Pure logic, no I/O, no pipeline wiring.
- **`backend/app/digests/`** — digest generation (Task 008).
- **`frontend/`** — the React shell: typed API client + Zod schemas, a polling health badge,
  and pages for Dashboard, Items, Sources, Digests, Settings.

## The root-level `prompts/` and `sources/` decision

`prompts/` and `sources/` live at the **repository root**, *not* nested under `backend/`. This is
a deliberate decision (it resolves an earlier ambiguity):

- **Why root-level.** They are *content/configuration*, not application code. Prompt wording and
  the source registry are edited by a human curator and should be reviewable and diffable without
  digging into the backend package. Keeping them at the root keeps that editorial surface
  obvious, and keeps them reusable by future components (e.g. a separate job runner) without a
  backend dependency.
- **How the backend resolves them.** Paths are **configurable**, never hard-coded. `core/config`
  reads `PROMPTS_DIR` (default `prompts`) and `SOURCES_FILE` (default `sources/sources.yaml`)
  from the environment and resolves them against the repository root (the parent of `backend/`).
  This means the backend has no embedded assumption about the directory layout — change the env
  var and the content can live anywhere, including a mounted volume in a future container setup.

## Later architecture (directional, not committed)

As the system grows beyond a single user or a single machine — **only when a task file calls for
it** — likely evolutions include: moving from SQLite to Postgres; introducing a vector store for
semantic dedup and similarity; a proper job scheduler/queue; and packaging via the (currently
inert) `docker-compose.yml`. None of this is built now; each is gated behind the exclusions in
`CLAUDE.md` and would be recorded as an ADR before adoption.

## Cross-cutting invariants (enforced in design)

- **Preserve every source URL.** The URL is a first-class field on RawItem and survives into
  EnrichedItem, the dashboard, and the digest.
- **Fail safely per source.** Ingestion isolates each source so one failure cannot abort a run.
- **Fact vs. interpretation.** Enrichment outputs keep the source fact separate from the model's
  interpretation; the data model and prompts reflect this split.
- **Scoring polarity / hype inversion.** Encoded in `scoring/` and honoured by ranking: hype is a
  demotion, never an additive term. See the brief's canonical scoring section.
- **One priority rule.** `scoring/priority.py` is the single source of truth; enrichment imports
  it rather than re-implementing it.
