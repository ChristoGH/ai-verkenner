"""Store client tests (M2) — ping() reports reachability and never raises.

No live containers: the underlying client/driver is patched to succeed or fail.
"""

from app.db import neo4j, qdrant


# ---- Qdrant ----


def test_qdrant_ping_ok(monkeypatch):
    class _Fine:
        def get_collections(self):
            return []

    monkeypatch.setattr(qdrant, "get_client", lambda: _Fine())
    status = qdrant.ping()
    assert status.name == "qdrant"
    assert status.status == "ok"
    assert status.ok is True


def test_qdrant_ping_unreachable_does_not_raise(monkeypatch):
    class _Boom:
        def get_collections(self):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(qdrant, "get_client", lambda: _Boom())
    status = qdrant.ping()  # must not raise
    assert status.status == "unreachable"
    assert status.ok is False
    assert "connection refused" in (status.detail or "")


# ---- Neo4j ----


def test_neo4j_ping_ok(monkeypatch):
    class _Fine:
        def verify_connectivity(self):
            return None

    monkeypatch.setattr(neo4j, "get_driver", lambda: _Fine())
    status = neo4j.ping()
    assert status.name == "neo4j"
    assert status.status == "ok"


def test_neo4j_ping_unreachable_does_not_raise(monkeypatch):
    class _Boom:
        def verify_connectivity(self):
            raise RuntimeError("no route to host")

    monkeypatch.setattr(neo4j, "get_driver", lambda: _Boom())
    status = neo4j.ping()  # must not raise
    assert status.status == "unreachable"
    assert "no route to host" in (status.detail or "")
