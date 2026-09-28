from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

_AUTH_HEADER = {"Authorization": "Bearer jwt-de-teste"}


@contextmanager
def _client():
    """TestClient com o checkpointer do grafo mockado — ele é construído na
    hora que `graph.py` é importado (dentro da rota) — e o índice de memória
    de longo prazo mockado, já que ele roda de verdade no lifespan e senão
    cada teste tentaria uma conexão real com o Mongo."""
    with (
        patch(
            "src.memory.session.mongo_checkpointer.create_mongo_checkpointer",
            return_value=InMemorySaver(),
        ),
        patch(
            "src.api.app.ensure_user_memory_indexes",
            new=AsyncMock(),
        ),
    ):
        from src.api.app import app

        with TestClient(app) as client:
            yield client


def test_chat_calls_execute_turn_and_maps_response(monkeypatch):
    fake_message = AIMessage(
        content="Recomendo um instalador na região.",
        additional_kwargs={
            "specialists_used": ["professional_suggester"],
            "workflow_steps": ["router", "professional_suggester", "orchestrator"],
        },
    )
    fake_final_state = {"messages": [fake_message]}

    mock_execute_turn = AsyncMock(return_value=fake_final_state)
    monkeypatch.setattr("src.api.routes.chat.execute_turn", mock_execute_turn)

    with _client() as client:
        response = client.post(
            "/chat",
            json={"conversation_id": "conv-1", "message": "Preciso de instalador"},
            headers=_AUTH_HEADER,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "Recomendo um instalador na região."
    assert body["specialists_used"] == ["professional_suggester"]
    assert body["workflow_steps"] == [
        "router",
        "professional_suggester",
        "orchestrator",
    ]

    mock_execute_turn.assert_awaited_once()
    called_args = mock_execute_turn.call_args.args
    called_kwargs = mock_execute_turn.call_args.kwargs
    assert called_args[0] == "conv-1"
    assert called_args[1] == "Preciso de instalador"
    assert called_kwargs["user_token"] == "jwt-de-teste"


def test_chat_falls_back_to_turn_agents_when_no_metadata(monkeypatch):
    fake_message = AIMessage(content="Resposta direta.", additional_kwargs={})
    fake_final_state = {
        "messages": [fake_message],
        "turn_agents": ["router_direct_response"],
    }

    mock_execute_turn = AsyncMock(return_value=fake_final_state)
    monkeypatch.setattr("src.api.routes.chat.execute_turn", mock_execute_turn)

    with _client() as client:
        response = client.post(
            "/chat",
            json={"conversation_id": "conv-2", "message": "Oi"},
            headers=_AUTH_HEADER,
        )

    body = response.json()
    assert body["specialists_used"] == []
    assert body["workflow_steps"] == ["router_direct_response"]


def test_chat_401_sem_header_authorization():
    with _client() as client:
        response = client.post(
            "/chat", json={"conversation_id": "conv-3", "message": "Oi"}
        )
    assert response.status_code == 401  # authorization é Header(None) opcional; 401 é levantado na rota


def test_chat_401_header_mal_formado():
    with _client() as client:
        response = client.post(
            "/chat",
            json={"conversation_id": "conv-3", "message": "Oi"},
            headers={"Authorization": "jwt-sem-bearer"},
        )
    assert response.status_code == 401


def test_app_import_does_not_touch_mongo_at_module_level():
    """O import de src.api.app não deve tentar conectar no Mongo sozinho."""
    import importlib

    import src.api.app as app_module

    importlib.reload(app_module)
    assert app_module.app is not None