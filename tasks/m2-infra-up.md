# Task M2 — Infra up (Docker Compose: Qdrant + Neo4j)

**Status: DONE** ✅ (commit `5a9e542`, branch `feat/m2-infra-up`)

> Traceability stub. M2 was built ahead of a dedicated task file (the original task files 002–008
> predate the milestone ladder). This file records the milestone for the `tasks/` index; the full
> specification lives in [`../docs/PHASE_1_PLAN.md`](../docs/PHASE_1_PLAN.md) §5 (M2).

## Goal

Bring Qdrant + Neo4j online via local Docker Compose, give the backend thin clients for both, and
make `/health` a per-dependency readiness report that **degrades rather than crashes** when a store
is down.

## Scope (as built)

- `docker-compose.yml`: `qdrant`, `neo4j:5` (capped heap/pagecache, cypher-shell healthcheck),
  `backend`, `frontend` dev services; named volumes; Dockerfiles + `.dockerignore`s.
- `app/db/qdrant.py` and `app/db/neo4j.py`: lazy client/driver with a non-raising `ping()`
  returning a shared `DependencyStatus`; `close()` wired into a FastAPI lifespan.
- `GET /health` stays backward-compatible (200, `status/service/version`) and adds
  `dependencies: {qdrant, neo4j}`; new `GET /health/ready` returns 503 until all stores reachable.
  `/health` never 5xx's on a store outage.
- Config/env: `QDRANT_URL`, `NEO4J_URI/USER/PASSWORD`, `STORE_PING_TIMEOUT`.

## Non-goals

No schemas, persistence, embeddings, LLM, or graph writes (those are M3+). Connectivity only.

## Acceptance criteria (met)

- `docker compose up` starts the four services and tears down cleanly.
- App boots and `/health` returns 200 with both deps reported, even when both stores are down.
- `/health/ready` returns 503 while a store is unreachable, 200 when all are up.
- Existing tests still pass; new client/health tests need no live containers.

## Constraints

One slice; human review gate before merge; SQLite-as-truth invariant respected (no writes here).
