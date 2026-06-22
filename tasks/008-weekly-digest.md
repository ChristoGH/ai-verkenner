# Task 008 (M7 — Feedback + GraphRAG digest) — Weekly Digest

**Status: M7 — IN REVIEW** (implemented on `feat/m7-feedback-digest`; awaiting review gate)

Implemented as a **GraphRAG** generator (`app/digests/`): embed the period's themes → Qdrant
retrieve → Neo4j expand → one composition LLM call (or the deterministic fallback render). It
composes over **already-enriched** Events (enrichment is never re-run), reuses `rank_with_graph` /
`graph_signals` (no re-derivation of ranking or the priority rule), and degrades to SQLite-only when
the stores are down. Persisted as `Digest`; `GET /digests` + `GET /digests/{id}`; a Digests page in
the frontend. The weak-signals / research-radar sections draw from the hub-dampened convergence
quadrant; the noise count is the honest archived/high-hype total. Covered by
`backend/tests/test_digest.py` + the Digests page test. The CLI generates: `python -m app.cli digest`.

## Goal

Generate the decision-oriented weekly digest from real enriched items, store it as a `Digest`,
and make it readable.

## Scope

- A digest generator that selects and organises the week's enriched items using the
  `prompts/digest.md` template.
- A `Digest` entity referencing the items it drew from, with the generated content.
- `GET /digests` and `GET /digests/{id}`, and a simple Digests page in the frontend.
- Digest structure (decision-oriented, not a link list): executive summary, must-know,
  should-read, weak signals, research radar, tool changes, risks, opportunities, suggested
  experiments, and an ignored/noise count.

## Non-goals

- No email/Slack/Teams delivery (excluded by `CLAUDE.md`).
- No scheduling infrastructure beyond a manual/triggered generate for the MVP.
- No new scoring — reuse priority classes and the hype inversion.

## Acceptance criteria

- A digest generates from real enriched items and persists as a `Digest`.
- It reads as **decisions**: each section earns its place; the must-know section is short and
  actionable; the noise count is honest.
- Weak signals and research-radar sections reflect the `horizon_signal` quadrant.
- Every referenced item keeps its source link.

## Files likely to change

`backend/app/digests/`, `backend/app/models/` (`Digest`), `backend/app/api/`,
`frontend/src/pages/Digests.tsx`, `prompts/digest.md` (tightening), `backend/tests/`.

## Test plan

- Backend: generate a digest from a fixture set of enriched items; assert all sections present
  and the noise count matches the archived/high-hype items.
- API: `GET /digests` and `GET /digests/{id}` return the stored digest.

## Agent constraints

- Decision-oriented, not a link dump. Preserve source links. Respect priority classes and the
  hype inversion when selecting/ordering.
- One slice; stop at the review gate.

## Paste-ready agent prompt

> Implement Task 008 (weekly-digest) per `tasks/008-weekly-digest.md`. Build a digest generator
> using `prompts/digest.md` that produces a decision-oriented weekly briefing (executive summary,
> must-know, should-read, weak signals, research radar, tool changes, risks, opportunities,
> suggested experiments, ignored/noise count) from real enriched items, persist it as a `Digest`,
> and expose `GET /digests` + `GET /digests/{id}` with a Digests page. Preserve source links;
> respect priority classes and the hype inversion. Add tests. Work on `feat/008-weekly-digest`;
> stop at the review gate.
