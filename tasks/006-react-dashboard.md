# Task 006 (M6 — Dashboard + Cosmograph) — React Dashboard (Core Radar)

**Status: M6 — IN REVIEW** (implemented on `feat/m6-dashboard`; awaiting review gate)

> **Scope note (PHASE_1_PLAN §5 extends this task).** Beyond the original Core Radar `/items`, M6
> also adds the **Cosmograph** `/graph` view (`@cosmograph/react`, Network + Timeline + Search,
> click-an-entity → filter the list) and the **`/horizon`** weak-signal view (the
> horizon_signal/archive quadrant ranked by graph convergence — the query that makes the "Weak
> Signal of the Week" reachable). A real-data smoke over live feeds + Neo4j + a cloud LLM is
> recorded in [`docs/m6-smoke-notes.md`](../docs/m6-smoke-notes.md).

## Goal

Build the Core Radar UI: a ranked feed of real `EnrichedItem` cards, wired to the backend through
the typed, Zod-validated client.

## Scope

- `GET /items` on the backend returning ranked enriched items (filterable, e.g. by priority
  class).
- A real `ItemCard` rendering: title, source, published date, priority badge, summary,
  why-it-matters, recommended action, the scores, and the **source link**.
- The Dashboard page lists items ranked by priority; the Items page allows filtering.
- All responses parsed through Zod schemas in `src/api/`.

## Non-goals

- No feedback actions yet (Task 007 — the buttons may be present but inert, or deferred).
- No digest UI (Task 008).
- No auth, no settings persistence beyond local UI state.

## Acceptance criteria

- The dashboard renders real ranked items end-to-end from the backend.
- Each card shows the source link and keeps fact (summary) visibly distinct from interpretation
  (why-it-matters).
- Priority badges reflect the backend's priority class.
- API responses are validated by Zod; a schema mismatch fails loudly in dev.

## Files likely to change

`backend/app/api/` (`/items`), `frontend/src/api/`, `frontend/src/components/ItemCard.tsx`,
`frontend/src/pages/Dashboard.tsx` and `Items.tsx`.

## Test plan

- Backend: `GET /items` returns ranked items with the expected shape.
- Frontend: the card renders all fields; Zod rejects a malformed payload in tests.
- Manual: dashboard shows items in priority order with working source links.

## Agent constraints

- Reuse the typed client and Zod patterns from the scaffold; don't bypass validation.
- Preserve and display every source URL. Keep fact and interpretation visually separate.
- One slice; stop at the review gate.

## Paste-ready agent prompt

> Implement Task 006 (react-dashboard) per `tasks/006-react-dashboard.md`. Add `GET /items`
> (ranked enriched items) and build the Core Radar dashboard: a real `ItemCard` (title, source,
> date, priority badge, summary, why-it-matters, recommended action, scores, source link) wired
> through the Zod-validated client. Keep fact separate from interpretation; show every source
> link. Add backend and frontend tests. Work on `feat/006-react-dashboard`; stop at the review
> gate.
