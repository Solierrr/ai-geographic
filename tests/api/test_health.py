from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_health_returns_ok_when_settings_present(monkeypatch):
    monkeypatch.setattr("src.api.app.settings.GOOGLE_API_KEY", "fake-key")
    monkeypatch.setattr("src.api.app.settings.GROQ_API_KEY", "fake-key")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "missing_settings": []}


def test_health_reports_missing_settings(monkeypatch):
    monkeypatch.setattr("src.api.app.settings.GOOGLE_API_KEY", None)
    monkeypatch.setattr("src.api.app.settings.GROQ_API_KEY", None)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "atencao"
    assert "GOOGLE_API_KEY" in body["missing_settings"]
    assert "GROQ_API_KEY" in body["missing_settings"]
