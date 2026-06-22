"""`/items/{id}/feedback` router — record a feedback action (M7).

The dashboard's item `id` is the **Event id** (enrichment is per-Event), so feedback is recorded
against the Event. The action is validated against the canonical list in `app/scoring/feedback.py`;
an unknown action is a 422. Feedback is append-only — the ranking layer collapses it to the latest
action per Event (see `scoring/feedback.latest_feedback`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.deps import session_dep
from app.models import Event, Feedback
from app.schemas.api import FeedbackIn, FeedbackOut
from app.scoring.feedback import FEEDBACK_ACTIONS

router = APIRouter(tags=["feedback"])


@router.post("/items/{item_id}/feedback", response_model=FeedbackOut, status_code=201)
def record_feedback(
    item_id: int,
    body: FeedbackIn,
    session: Session = Depends(session_dep),
) -> FeedbackOut:
    """Persist a feedback action (useful / not_useful / save / ignore) for an Event."""
    action = body.action.strip().lower()
    if action not in FEEDBACK_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"unknown action {body.action!r}; expected one of {list(FEEDBACK_ACTIONS)}",
        )
    if session.get(Event, item_id) is None:
        raise HTTPException(status_code=404, detail=f"no such item (event) {item_id}")

    row = Feedback(event_id=item_id, action=action)
    session.add(row)
    session.commit()
    session.refresh(row)
    return FeedbackOut(
        id=row.id,
        event_id=row.event_id,
        action=row.action,
        created_at=row.created_at.isoformat(),
    )
