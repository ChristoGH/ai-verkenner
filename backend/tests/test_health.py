"""Health & readiness endpoint tests (M2).

No live containers: the store pings are patched. These prove /health stays backward-compatible and
always 200 (degrade, never crash), and that /health/ready flips to 503 when a required store is
down.
"""

from fastapi.testclient import TestClient

from app.db import DependencyStatus
from app.db import neo4j as neo4j_db
from app.db import qdrant as qdrant_db
from app.main import app

client = TestClient(app)


def _patch_pings(monkeypatch, qdrant_status: str, neo4j_status: str) -> None:
    monkeypatch.setattr(qdrant_db, "ping", lambda: DependencyStatus("qdrant", qdrant_status))
    monkeypatch.setattr(neo4j_db, "ping", lambda: DependencyStatus("neo4j", neo4j_status))


def test_health_returns_ok_backward_compatible(monkeypatch):
    # The original contract must hold unchanged.
    _patch_pings(monkeypatch, "ok", "ok")
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "ai-verkenner"
    assert body["version"] == "0.1.0"


def test_health_reports_dependencies_when_up(monkeypatch):
    _patch_pings(monkeypatch, "ok", "ok")
    body = client.get("/health").json()
    assert body["dependencies"] == {"qdrant": "ok", "neo4j": "ok"}


def test_health_degrades_when_both_stores_down(monkeypatch):
    # The headline M2 guarantee: stores down -> still 200, status still "ok", deps unreachable.
    _patch_pings(monkeypatch, "unreachable", "unreachable")
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["dependencies"] == {"qdrant": "unreachable", "neo4j": "unreachable"}


def test_health_reports_mixed_state(monkeypatch):
    _patch_pings(monkeypatch, "ok", "unreachable")
    body = client.get("/health").json()
    assert body["dependencies"] == {"qdrant": "ok", "neo4j": "unreachable"}


def test_ready_returns_200_when_all_up(monkeypatch):
    _patch_pings(monkeypatch, "ok", "ok")
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_ready_returns_503_when_a_store_is_down(monkeypatch):
    _patch_pings(monkeypatch, "ok", "unreachable")
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["dependencies"]["neo4j"]["status"] == "unreachable"


def test_health_boots_and_degrades_through_real_ping_path(monkeypatch):
    """End-to-end degrade: with the real ping() code and clients that fail, /health is still 200.

    Simulates 'both stores down' by making the underlying clients raise; ping() must catch and
    report 'unreachable', and the app must serve /health without crashing.
    """

    class _BoomQdrant:
        def get_collections(self):
            raise RuntimeError("connection refused")

    class _BoomNeo4j:
        def verify_connectivity(self):
            raise RuntimeError("no route to host")

    monkeypatch.setattr(qdrant_db, "get_client", lambda: _BoomQdrant())
    monkeypatch.setattr(neo4j_db, "get_driver", lambda: _BoomNeo4j())

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["dependencies"] == {
        "qdrant": "unreachable",
        "neo4j": "unreachable",
    }
