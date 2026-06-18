# Task 007 — Feedback Actions

**Status: TODO**

## Goal

Add the feedback loop: useful / not useful / save / ignore, persisted and folded back into
ranking.

## Scope

- A `Feedback` entity (`item_id`, `action` ∈ {useful, not_useful, save, ignore}, timestamp).
- `POST /items/{id}/feedback` to record an action.
- Wire the `ItemCard` feedback buttons to the endpoint via the typed client.
- Fold feedback into ranking: `useful`/`save` lift, `not_useful`/`ignore` demote; `ignore`
  removes the item from the default view.

## Non-goals

- No machine-learned personalisation model — a transparent, rule-based adjustment is enough.
- No digest changes (Task 008).
- No multi-user (feedback is the single user's).

## Acceptance criteria

- Feedback persists via `POST /items/{id}/feedback`.
- Feedback observably changes ordering (e.g. an `ignore`d item leaves the default feed; a
  `useful` item ranks higher than an equivalent un-rated one).
- The adjustment rule is documented and respects the existing scoring polarity (hype stays a
  demotion).

## Files likely to change

`backend/app/models/` (`Feedback`), `backend/app/api/`, ranking logic, `frontend/src/api/`,
`frontend/src/components/ItemCard.tsx`, `backend/tests/`, frontend tests.

## Test plan

- Backend: posting each action persists it; ranking reflects it deterministically.
- Frontend: clicking a button calls the endpoint and updates the view optimistically.

## Agent constraints

- Keep the ranking adjustment simple, transparent, and consistent with the canonical scoring
  (don't break the hype inversion or the priority rule).
- One slice; stop at the review gate.

## Paste-ready agent prompt

> Implement Task 007 (feedback-actions) per `tasks/007-feedback-actions.md`. Add a `Feedback`
> entity and `POST /items/{id}/feedback`, wire the `ItemCard` buttons (useful / not useful / save
> / ignore), and fold feedback into ranking transparently (ignore removes from default view;
> useful/save lift; not_useful demote) without breaking the scoring polarity. Add backend and
> frontend tests. Work on `feat/007-feedback-actions`; stop at the review gate.
