# Task 004 (M3 — Storage + embeddings + semantic dedup) — Storage & Deduplication

**Status: M3 — IN REVIEW** (implemented on `feat/m3-storage-dedup`; awaiting review gate)

> **Scope note (ADR 0001 / PHASE_1_PLAN §5 supersede the original body below).** This task's
> original draft predates the graph/vector adoption and said "no vector store". M3 now *adds*
> Qdrant embeddings + two-stage semantic dedup → `Event`s on top of the SQLite persistence. SQLite
> remains the source of truth; Qdrant is a rebuildable derived index. See the milestone detail in
> [`docs/PHASE_1_PLAN.md`](../docs/PHASE_1_PLAN.md) (M3).

## Goal

Persist ingested items to SQLite (SQLModel/SQLAlchemy) for `Source`, `RawItem`, and `Event`; embed
new items with a local model into the Qdrant `items` collection; and de-duplicate near-identical
coverage into `Event`s. Repeated runs are idempotent (no duplicate rows, stable Event assignment).

## Scope

- A SQLite engine/session in `db/` and entity models in `models/` for `Source` and `RawItem`
  (with room for `EnrichedItem`, `Feedback`, `Digest` to follow).
- Persist sources (from the registry) and raw items (from ingestion).
- **Deduplication**: a stable hash over identifying fields (e.g. source + canonical URL +
  title/published) so an item already stored is recognised and not re-inserted.
- A minimal "run" path: ingest → dedup → persist new items only.

## Non-goals

- No enrichment/scoring (Task 005 / M4); `priority.py` stays untouched and unimported here.
- No entity/relationship extraction, no Neo4j writes (M4/M5), no Cosmograph (M6).
- No real `github_*` intelligence fetchers (they stay M1 stubs — a separate slice).
- No migrations framework beyond what SQLite needs for the MVP (keep it simple; document the
  schema).
- No Postgres. (Qdrant *is* in scope at M3, per ADR 0001 — superseding the original draft.)

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
