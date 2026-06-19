# Task 003 (M1 — Source registry + ingestion) — RSS / GitHub / arXiv Ingestion

**Status: M1 — IN PROGRESS** (implemented in `feat/m1-source-ingestion`; awaiting review gate)

## Goal

Fetch each enabled source and turn it into in-memory `RawItem`s — RSS/Atom via `feedparser`,
GitHub releases and arXiv via `httpx`. **Fail safely per source.**

## Scope

- An ingestion module that, given the validated registry, fetches each enabled source by
  `source_type`.
- A `RawItem` shape: source reference, title, **source URL (always preserved)**, published
  timestamp, raw content/summary.
- Per-source error isolation: a failing source (network error, malformed feed, HTTP error) is
  logged and skipped; the run continues and reports which sources succeeded/failed.
- Reasonable timeouts and a polite user agent.

## Non-goals

- No persistence yet (Task 004) — items are produced in memory / returned.
- No deduplication yet (Task 004).
- No enrichment or scoring (Task 005).

## Acceptance criteria

- A run over the registry produces `RawItem`s from the working sources.
- A deliberately broken source (bad URL / malformed feed) does **not** abort the run; it is
  logged and skipped, and the run reports it.
- Every produced item carries its source URL.

## Files likely to change

`backend/app/ingestion/` (fetchers per source type + an orchestrator), `backend/app/models/`
(or schemas) for `RawItem`, `backend/tests/` with recorded/fixture feeds.

## Test plan

- Unit: parse a fixture RSS feed; parse a fixture GitHub releases payload; build an arXiv query
  URL.
- Resilience: an orchestrator run with one good and one broken source yields the good items and
  reports the failure without raising.

## Agent constraints

- **Fail safely per source** is the headline invariant here — never let one source break a run.
- Preserve every source URL. Use timeouts; don't hammer sources.
- No DB writes (that's 004). One slice; stop at the review gate.

## Paste-ready agent prompt

> Implement Task 003 (rss-github-ingestion) per `tasks/003-rss-github-ingestion.md`. Add fetchers
> for RSS/Atom (`feedparser`), GitHub releases and arXiv (`httpx`), and an orchestrator that runs
> the enabled registry into in-memory `RawItem`s, isolating per-source failures (log + skip +
> report). Preserve every source URL. No persistence, no enrichment. Add fixture-based and
> resilience tests. Work on `feat/003-rss-github-ingestion`; stop at the review gate.
