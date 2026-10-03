from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_health_returns_ok_when_settings_present(monkeypatch):
    monkeypatch.setattr("src.api.app.settings.GOOGLE_REGISTRY_URL", "http://registry")
    monkeypatch.setattr("src.api.app.settings.REGISTRY_CONSUMER_TOKEN", "fake-key")
    monkeypatch.setattr("src.api.app.settings.GOOGLE_MAPS_API_KEY", "fake-key")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "missing_settings": []}


def test_health_reports_missing_settings(monkeypatch):
    monkeypatch.setattr("src.api.app.settings.GOOGLE_REGISTRY_URL", None)
    monkeypatch.setattr("src.api.app.settings.REGISTRY_CONSUMER_TOKEN", None)
    monkeypatch.setattr("src.api.app.settings.GOOGLE_MAPS_API_KEY", None)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "atencao"
    assert "GOOGLE_REGISTRY_URL" in body["missing_settings"]
    assert "REGISTRY_CONSUMER_TOKEN" in body["missing_settings"]
    assert "GOOGLE_MAPS_API_KEY" in body["missing_settings"]
