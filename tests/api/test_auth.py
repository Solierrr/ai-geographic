from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from src.core.config.settings import settings

_BODY = {"conversation_id": "conv-1", "message": "oi"}
_AUTH_HEADER = {"Authorization": "Bearer jwt-de-teste"}


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


@pytest.fixture
def jwks_configurado(monkeypatch):
    monkeypatch.setattr(settings, "JWT_JWKS_URL", "https://auth.exemplo.com/jwks.json")
    monkeypatch.setattr(settings, "ENVIRONMENT", "QA")


def test_chat_401_com_token_que_o_api_auth_nao_assinou(monkeypatch, jwks_configurado):
    execute_turn = AsyncMock()
    monkeypatch.setattr("src.api.routes.chat.execute_turn", execute_turn)
    monkeypatch.setattr("src.api.auth.is_valid_access_token", lambda token: False)

    with _client() as client:
        response = client.post("/chat", json=_BODY, headers=_AUTH_HEADER)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    execute_turn.assert_not_awaited()


def test_chat_segue_com_token_valido(monkeypatch, jwks_configurado):
    final_state = {"messages": [AIMessage(content="Oi!", additional_kwargs={})]}
    execute_turn = AsyncMock(return_value=final_state)
    monkeypatch.setattr("src.api.routes.chat.execute_turn", execute_turn)
    monkeypatch.setattr("src.api.auth.is_valid_access_token", lambda token: True)

    with _client() as client:
        response = client.post("/chat", json=_BODY, headers=_AUTH_HEADER)

    assert response.status_code == 200
    assert execute_turn.call_args.kwargs["user_token"] == "jwt-de-teste"


def test_chat_falha_fechada_fora_do_local_sem_jwks(monkeypatch):
    monkeypatch.setattr(settings, "JWT_JWKS_URL", None)
    monkeypatch.setattr(settings, "ENVIRONMENT", "QA")
    execute_turn = AsyncMock()
    monkeypatch.setattr("src.api.routes.chat.execute_turn", execute_turn)

    with _client() as client:
        response = client.post("/chat", json=_BODY, headers=_AUTH_HEADER)

    assert response.status_code == 503
    execute_turn.assert_not_awaited()


def test_chat_local_sem_jwks_nao_valida(monkeypatch):
    final_state = {"messages": [AIMessage(content="Oi!", additional_kwargs={})]}
    monkeypatch.setattr(
        "src.api.routes.chat.execute_turn", AsyncMock(return_value=final_state)
    )

    with _client() as client:
        response = client.post("/chat", json=_BODY, headers=_AUTH_HEADER)

    assert response.status_code == 200
