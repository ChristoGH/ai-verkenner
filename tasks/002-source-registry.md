# Task 002 — Source Registry

**Status: TODO**

## Goal

Load and validate the curated source registry (`sources/sources.yaml`) through configurable
paths, model a `Source`, and expose it via `GET /sources`. This is the first real read of
root-level content by the backend.

## Scope

- A `Source` schema/model (Pydantic for now; persistence comes in 004) with: `name`,
  `source_type`, `url`, optional `repo_owner`/`repo_name`/`arxiv_query`, `enabled`,
  `trust_level`.
- `core/config` resolves `SOURCES_FILE` (default `sources/sources.yaml`) relative to the repo
  root.
- A loader that parses the YAML, validates each entry, and reports malformed entries clearly
  (which file, which entry, what's wrong) without crashing the app.
- `GET /sources` returning the validated, configured sources (optionally filterable by
  `enabled`).

## Non-goals

- No fetching or parsing of the sources themselves (that is Task 003).
- No database persistence yet (Task 004).
- No editing of sources via the API (registry is human-curated, file-based).

## Acceptance criteria

- The app loads `sources.yaml` via the configured path and exposes `GET /sources`.
- A malformed entry produces a clear, localised validation error rather than a silent drop or a
  crash.
- `source_type` is constrained to a known set (e.g. `rss`, `github_releases`, `arxiv`).
- `trust_level` and `enabled` are validated.

## Files likely to change

`backend/app/core/config.py`, `backend/app/models/` (or a `schemas/`), a new
`backend/app/sources/` loader, `backend/app/api/` router, `backend/tests/`.

## Test plan

- Unit: loader parses a valid fixture; rejects fixtures with bad `source_type`, missing `url`,
  bad `trust_level`.
- API: `GET /sources` returns the expected count and fields; honours an `enabled` filter.

## Agent constraints

- Path is configurable, never hard-coded (see `CLAUDE.md` and `TECHNICAL_DESIGN.md`).
- Preserve URLs exactly as written. Fail safely on a bad registry — surface the error, don't
  crash the process.
- One slice; stop at the review gate.

## Paste-ready agent prompt

> Implement Task 002 (source-registry) per `tasks/002-source-registry.md`. Add a validated
> `Source` model, load `sources/sources.yaml` through `core/config` using the configurable
> `SOURCES_FILE` path, and expose `GET /sources`. Report malformed entries clearly without
> crashing. No fetching, no DB. Add tests for valid and invalid registries. Work on
> `feat/002-source-registry`; stop at the review gate.
