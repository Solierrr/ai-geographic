from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from src.api.app import cors_origins
from src.core.config.settings import Settings


@contextmanager
def _client():
    with (
        patch(
            "src.memory.session.mongo_checkpointer.create_mongo_checkpointer",
            return_value=InMemorySaver(),
        ),
        patch("src.api.app.ensure_user_memory_indexes", new=AsyncMock()),
    ):
        from src.api.app import app

        with TestClient(app) as client:
            yield client


def test_preflight_libera_a_origem_do_portal():
    origem = "https://web-sandbox-7ug0.onrender.com"

    with _client() as client:
        response = client.options(
            "/chat",
            headers={
                "Origin": origem,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origem


def test_preflight_nao_libera_origem_desconhecida():
    with _client() as client:
        response = client.options(
            "/chat",
            headers={
                "Origin": "https://outro-site.exemplo.com",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert "access-control-allow-origin" not in response.headers


def test_cors_origins_separa_por_virgula_e_ignora_vazios():
    assert cors_origins(" https://a.com ,, https://b.com,") == [
        "https://a.com",
        "https://b.com",
    ]
    assert cors_origins("") == []


def test_settings_le_as_origens_do_ambiente(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://portal.exemplo.com")

    assert Settings().CORS_ALLOWED_ORIGINS == "https://portal.exemplo.com"


@pytest.mark.parametrize("origem", ["http://localhost:5173", "http://localhost:3000"])
def test_default_inclui_as_origens_locais(origem):
    assert origem in cors_origins(Settings().CORS_ALLOWED_ORIGINS)
