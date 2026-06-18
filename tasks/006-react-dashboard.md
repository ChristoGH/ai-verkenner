# Task 006 — React Dashboard (Core Radar)

**Status: TODO**

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
