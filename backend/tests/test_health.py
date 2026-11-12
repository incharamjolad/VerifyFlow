from fastapi.testclient import TestClient
from app.main import app
from app.database import mongo

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_when_db_down(monkeypatch):
    monkeypatch.setattr(mongo, "ping", lambda: False)
    assert client.get("/ready").status_code == 503


def test_ready_when_db_up(monkeypatch):
    monkeypatch.setattr(mongo, "ping", lambda: True)
    assert client.get("/ready").json()["status"] == "ready"
