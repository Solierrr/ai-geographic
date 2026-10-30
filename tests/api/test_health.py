from fastapi.testclient import TestClient

from src.api.routes import health
from src.api.app import app
from src.version import VERSION

client = TestClient(app)


def test_health_returns_up_with_version():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP", "version": VERSION}


def test_ready_returns_up_when_mongo_answers(monkeypatch):
    async def ping():
        return None

    monkeypatch.setattr(health, "_ping_mongo", ping)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_ready_returns_down_when_mongo_fails(monkeypatch):
    async def ping():
        raise ConnectionError("mongo fora")

    monkeypatch.setattr(health, "_ping_mongo", ping)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "DOWN"}
