"""Feedback (M7) — persists, folds into ranking transparently, never changes the priority class.

Offline: in-memory SQLite + the FastAPI app with the session dependency overridden. Asserts the
contract from tasks/007: posting persists; an `ignore`d item leaves the default feed; a `useful`
item ranks above an equivalent un-rated one — all without moving any item between priority classes.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import dashboard_service
from app.api.deps import graph_store_dep, session_dep
from app.main import app
from app.models import Feedback
from app.scoring.feedback import latest_feedback
from tests import graph_helpers as gh


def _two_equivalent_horizon_items(session):
    """Two horizon_signal Events with identical scores → tie-broken only by feedback."""
    s1 = gh.add_source(session, "src1")
    events = []
    for i in (1, 2):
        ev = gh.add_event(session, f"equivalent dev {i}")
        item = gh.add_item(session, s1, ev, title=f"Dev {i}", url=f"https://src1/{i}")
        gh.add_enriched(session, ev, item, priority_class="horizon_signal",
                        relevance=1, novelty=2, actionability=2, strategic_potential=4, hype=1)
        events.append(ev)
    return events


def _client(session):
    app.dependency_overrides[session_dep] = lambda: session
    app.dependency_overrides[graph_store_dep] = lambda: None  # graph-less; isolate feedback effect
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


# ---- persistence ----


def test_post_feedback_persists(session):
    ev = gh.add_event(session, "dev")
    s1 = gh.add_source(session, "src1")
    item = gh.add_item(session, s1, ev, title="t", url="https://src1/t")
    gh.add_enriched(session, ev, item, priority_class="operational_update")
    tc = _client(session)

    resp = tc.post(f"/items/{ev.id}/feedback", json={"action": "useful"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["event_id"] == ev.id and body["action"] == "useful"
    from sqlmodel import select
    stored = session.exec(select(Feedback)).all()
    assert len(stored) == 1 and stored[0].action == "useful"


def test_unknown_action_is_rejected(session):
    ev = gh.add_event(session, "dev")
    tc = _client(session)
    resp = tc.post(f"/items/{ev.id}/feedback", json={"action": "love-it"})
    assert resp.status_code == 422


def test_feedback_on_missing_event_is_404(session):
    tc = _client(session)
    resp = tc.post("/items/9999/feedback", json={"action": "useful"})
    assert resp.status_code == 404


# ---- ranking effect (transparent, class-preserving) ----


def test_useful_ranks_above_equivalent_unrated(session):
    ev_a, ev_b = _two_equivalent_horizon_items(session)
    tc = _client(session)

    # Before feedback the two are equivalent; mark B useful → B should rank first.
    tc.post(f"/items/{ev_b.id}/feedback", json={"action": "useful"})
    ids = [it["id"] for it in tc.get("/items").json()]
    assert ids[0] == str(ev_b.id)
    # And the class is unchanged (both still horizon_signal).
    classes = {it["id"]: it["priority_class"] for it in tc.get("/items").json()}
    assert classes[str(ev_b.id)] == "horizon_signal"
    assert classes[str(ev_a.id)] == "horizon_signal"


def test_not_useful_demotes(session):
    ev_a, ev_b = _two_equivalent_horizon_items(session)
    tc = _client(session)
    tc.post(f"/items/{ev_a.id}/feedback", json={"action": "not_useful"})
    ids = [it["id"] for it in tc.get("/items").json()]
    assert ids[0] == str(ev_b.id)  # the un-rated one now outranks the demoted A


def test_ignore_removes_from_default_feed(session):
    ev_a, ev_b = _two_equivalent_horizon_items(session)
    tc = _client(session)
    tc.post(f"/items/{ev_a.id}/feedback", json={"action": "ignore"})
    ids = [it["id"] for it in tc.get("/items").json()]
    assert str(ev_a.id) not in ids
    assert str(ev_b.id) in ids


def test_ignore_does_not_change_priority_class_of_others(session):
    ev_a, ev_b = _two_equivalent_horizon_items(session)
    tc = _client(session)
    tc.post(f"/items/{ev_a.id}/feedback", json={"action": "ignore"})
    body = tc.get("/items").json()
    assert all(it["priority_class"] == "horizon_signal" for it in body)


def test_latest_action_wins(session):
    ev_a, ev_b = _two_equivalent_horizon_items(session)
    tc = _client(session)
    # ignore then change mind → useful: A reappears and is not hidden.
    tc.post(f"/items/{ev_a.id}/feedback", json={"action": "ignore"})
    tc.post(f"/items/{ev_a.id}/feedback", json={"action": "useful"})
    ids = [it["id"] for it in tc.get("/items").json()]
    assert str(ev_a.id) in ids


def test_latest_feedback_helper_collapses_history(session):
    ev_a, _ev_b = _two_equivalent_horizon_items(session)
    rows = [
        Feedback(id=1, event_id=ev_a.id, action="useful"),
        Feedback(id=2, event_id=ev_a.id, action="ignore"),
    ]
    states = latest_feedback(rows)
    assert states[ev_a.id].action == "ignore" and states[ev_a.id].hidden is True
