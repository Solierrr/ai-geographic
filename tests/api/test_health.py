from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


class _Keys:
    def __init__(self, providers):
        self._providers = providers

    def providers(self):
        return self._providers


def test_health_returns_ok_when_keys_present(monkeypatch):
    monkeypatch.setattr("src.api.app.key_client", lambda: _Keys(["gemini", "groq"]))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "missing_settings": []}


def test_health_reports_missing_keys(monkeypatch):
    monkeypatch.setattr("src.api.app.key_client", lambda: _Keys([]))

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "atencao"
    assert "GEMINI_API_KEY" in body["missing_settings"]
    assert "GROQ_API_KEY" in body["missing_settings"]
