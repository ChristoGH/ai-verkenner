# Task 004 (M3 — Storage + embeddings + semantic dedup) — Storage & Deduplication

**Status: M3 — TODO**

## Goal

Introduce SQLite persistence (SQLModel/SQLAlchemy) for `Source` and `RawItem`, and deduplicate
raw items so repeated runs don't create duplicates.

## Scope

- A SQLite engine/session in `db/` and entity models in `models/` for `Source` and `RawItem`
  (with room for `EnrichedItem`, `Feedback`, `Digest` to follow).
- Persist sources (from the registry) and raw items (from ingestion).
- **Deduplication**: a stable hash over identifying fields (e.g. source + canonical URL +
  title/published) so an item already stored is recognised and not re-inserted.
- A minimal "run" path: ingest → dedup → persist new items only.

## Non-goals

- No enrichment/scoring (Task 005).
- No migrations framework beyond what SQLite needs for the MVP (keep it simple; document the
  schema).
- No Postgres, no vector store.

## Acceptance criteria

- Items persist to SQLite.
- A second run over the same sources adds **no** duplicate raw items.
- The dedup key is deterministic and documented.
- Source URLs are stored intact.

## Files likely to change

`backend/app/db/`, `backend/app/models/`, the ingestion-to-storage glue, `backend/tests/`.

## Test plan

- Unit: the dedup hash is stable for equal items and distinct for different ones.
- Integration: ingest a fixture set twice; assert row counts don't double.

## Agent constraints

- Keep the schema legible and forward-compatible with later entities.
- Preserve source URLs; dedup must not discard the canonical link.
- One slice; stop at the review gate.

## Paste-ready agent prompt

> Implement Task 004 (storage-deduplication) per `tasks/004-storage-deduplication.md`. Add SQLite
> via SQLModel/SQLAlchemy, persist `Source` and `RawItem`, and deduplicate raw items with a
> stable, documented hash so re-runs add no duplicates. No enrichment. Add unit tests for the
> dedup key and an integration test asserting idempotent re-runs. Work on
> `feat/004-storage-deduplication`; stop at the review gate.
