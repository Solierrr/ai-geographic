from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from src.core.config.settings import Settings, settings

ADMIN_SUB = "11111111-2222-3333-4444-555555555555"
OUTRO_SUB = "99999999-2222-3333-4444-555555555555"
_AUTH = {"Authorization": "Bearer jwt-de-teste"}
_BODY = {"conversation_id": "conv-1", "message": "oi"}


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
def debug_ligado(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG_ADMIN_SUBS", ADMIN_SUB)
    monkeypatch.setattr(settings, "ENVIRONMENT", "QA")
    monkeypatch.setattr("src.api.routes.debug.decode_user_id", lambda token: ADMIN_SUB)
    return settings


def _estado_final():
    return {
        "messages": [
            AIMessage(
                content="Resposta",
                additional_kwargs={
                    "specialists_used": ["action_proposer"],
                    "workflow_steps": ["router", "action_proposer"],
                },
            )
        ]
    }


def test_sem_admins_configurados_a_rota_responde_404(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG_ADMIN_SUBS", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "QA")

    with _client() as client:
        response = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert response.status_code == 404


def test_sem_token_responde_401(debug_ligado):
    with _client() as client:
        response = client.post("/debug/chat", json=_BODY)

    assert response.status_code == 401


def test_token_invalido_responde_401(debug_ligado, monkeypatch):
    monkeypatch.setattr("src.api.routes.debug.decode_user_id", lambda token: None)

    with _client() as client:
        response = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert response.status_code == 401


def test_nao_admin_responde_403(debug_ligado, monkeypatch):
    monkeypatch.setattr("src.api.routes.debug.decode_user_id", lambda token: OUTRO_SUB)

    with _client() as client:
        response = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert response.status_code == 403


def test_lista_de_admins_invalida_fecha_a_rota(debug_ligado, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG_ADMIN_SUBS", "nao-e-uuid, ,")

    with _client() as client:
        response = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert response.status_code == 404


@pytest.mark.parametrize("ambiente", ["PRD", "PRODUCTION", "staging", ""])
def test_fora_da_lista_de_ambientes_responde_404(debug_ligado, monkeypatch, ambiente):
    monkeypatch.setattr(settings, "ENVIRONMENT", ambiente)

    with _client() as client:
        response = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert response.status_code == 404


def test_admin_recebe_resposta_com_debug_dos_nos(debug_ligado, monkeypatch):
    chamada = {}

    async def fake_execute_turn(thread_id, message, workflow, **kwargs):
        collector = kwargs["extra_callbacks"][0]
        await collector.on_chain_start(
            {},
            {"route": ""},
            run_id="n1",
            metadata={"langgraph_node": "router"},
            name="router",
        )
        await collector.on_chain_end({"route": "action_proposer"}, run_id="n1")
        chamada.update(thread_id=thread_id, message=message, kwargs=kwargs)
        return _estado_final()

    monkeypatch.setattr("src.api.routes.debug.execute_turn", fake_execute_turn)

    with _client() as client:
        response = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "Resposta"
    assert body["specialists_used"] == ["action_proposer"]
    assert body["workflow_steps"] == ["router", "action_proposer"]
    assert body["debug"]["route"] == "action_proposer"
    assert body["debug"]["nodes"][0]["node"] == "router"
    assert body["debug"]["environment"] == "QA"
    assert body["debug"]["persisted"] is True
    assert chamada["thread_id"] == f"debug:{ADMIN_SUB}:conv-1"
    assert chamada["message"] == "oi"
    kwargs = chamada["kwargs"]
    assert kwargs["persist"] is False
    assert kwargs["save_history"] is True
    assert kwargs["user_token"] == "jwt-de-teste"


def test_falha_no_turno_devolve_500_com_debug_anonimizado(debug_ligado, monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.debug.execute_turn",
        AsyncMock(side_effect=RuntimeError("falhou para joao@exemplo.com")),
    )

    with _client() as client:
        response = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "RuntimeError: falhou para [EMAIL]"
    assert body["debug"]["nodes"] == []


def test_rota_fica_fora_do_openapi():
    with _client() as client:
        paths = client.get("/openapi.json").json()["paths"]

    assert "/debug/chat" not in paths
    assert "/chat" in paths


def test_chat_continua_igual_e_sem_flags_de_debug(monkeypatch):
    mock_execute_turn = AsyncMock(return_value=_estado_final())
    monkeypatch.setattr("src.api.routes.chat.execute_turn", mock_execute_turn)

    with _client() as client:
        response = client.post("/chat", json=_BODY, headers=_AUTH)

    assert response.status_code == 200
    assert "debug" not in response.json()
    kwargs = mock_execute_turn.await_args.kwargs
    assert "persist" not in kwargs
    assert "extra_callbacks" not in kwargs


@pytest.mark.parametrize("ambiente", ["LOCAL", "dev", "QA", " qa ", "PROD", "prod"])
def test_ambientes_permitidos_ignoram_caixa_e_espacos(
    debug_ligado, monkeypatch, ambiente
):
    monkeypatch.setattr(settings, "ENVIRONMENT", ambiente)
    monkeypatch.setattr(
        "src.api.routes.debug.execute_turn",
        AsyncMock(return_value=_estado_final()),
    )

    with _client() as client:
        response = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert response.status_code == 200


def test_em_prod_continua_exigindo_admin(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "PROD")
    monkeypatch.setattr(settings, "DEBUG_ADMIN_SUBS", "")

    with _client() as client:
        sem_admins = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert sem_admins.status_code == 404

    monkeypatch.setattr(settings, "DEBUG_ADMIN_SUBS", ADMIN_SUB)
    monkeypatch.setattr("src.api.routes.debug.decode_user_id", lambda token: OUTRO_SUB)

    with _client() as client:
        outro_usuario = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert outro_usuario.status_code == 403


def test_cada_turno_de_debug_deixa_log_com_sub_e_ambiente(
    debug_ligado, monkeypatch, caplog
):
    monkeypatch.setattr(settings, "ENVIRONMENT", "PROD")
    monkeypatch.setattr(
        "src.api.routes.debug.execute_turn",
        AsyncMock(return_value=_estado_final()),
    )

    with caplog.at_level("INFO", logger="src.api.routes.debug"):
        with _client() as client:
            client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert f"sub={ADMIN_SUB}" in caplog.text
    assert "ambiente=PROD" in caplog.text


def test_padrao_do_settings_nao_tem_admin_nem_flag_de_liga_desliga(monkeypatch):
    monkeypatch.delenv("DEBUG_ADMIN_SUBS", raising=False)
    padrao = Settings(_env_file=None)

    assert padrao.DEBUG_ADMIN_SUBS == ""
    assert not hasattr(padrao, "DEBUG_ENDPOINT_ENABLED")


_CUSTOM = {
    "turn": 0,
    "node": "router",
    "occurrence": 0,
    "stop_after_node": True,
    "prompts": [
        {
            "call": 0,
            "prompt": [
                {"type": "system", "content": "NOVO PROMPT"},
                {"type": "human", "content": "oi"},
            ],
        }
    ],
}


def test_execucao_personalizada_roda_so_o_no_e_confirma_no_debug(
    debug_ligado, monkeypatch
):
    chamada = {}

    async def fake_execute_single_node(thread_id, workflow, token, **kwargs):
        collector = kwargs["extra_callbacks"][0]
        await collector.on_chain_start(
            {}, {}, run_id="n1", metadata={"langgraph_node": "router"}, name="router"
        )
        await collector.on_chain_end({"route": "faq_reader"}, run_id="n1")
        chamada.update(thread_id=thread_id, token=token, kwargs=kwargs)
        return {}, ("faq_reader",), 1

    monkeypatch.setattr(
        "src.api.routes.debug.execute_single_node", fake_execute_single_node
    )

    with _client() as client:
        response = client.post(
            "/debug/chat", json={**_BODY, "custom": _CUSTOM}, headers=_AUTH
        )

    assert response.status_code == 200
    debug = response.json()["debug"]
    assert [n["node"] for n in debug["nodes"]] == ["router"]
    assert debug["custom"] == {
        "node": "router",
        "turn": 0,
        "occurrence": 0,
        "stopped": True,
        "overrides_applied": 1,
        "next": ["faq_reader"],
    }
    assert debug["persisted"] is False
    assert chamada["thread_id"] == f"debug:{ADMIN_SUB}:conv-1"
    assert chamada["kwargs"]["overrides"] == {0: {0: "NOVO PROMPT"}}
    assert chamada["kwargs"]["node"] == "router"


def test_execucao_personalizada_exige_admin(debug_ligado, monkeypatch):
    monkeypatch.setattr("src.api.routes.debug.decode_user_id", lambda token: OUTRO_SUB)

    with _client() as client:
        response = client.post(
            "/debug/chat", json={**_BODY, "custom": _CUSTOM}, headers=_AUTH
        )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "custom",
    [
        {**_CUSTOM, "node": "Router; DROP"},
        {**_CUSTOM, "stop_after_node": False},
        {**_CUSTOM, "turn": -1},
        {**_CUSTOM, "prompts": [_CUSTOM["prompts"][0], _CUSTOM["prompts"][0]]},
    ],
)
def test_execucao_personalizada_invalida_responde_400(debug_ligado, custom):
    with _client() as client:
        response = client.post(
            "/debug/chat", json={**_BODY, "custom": custom}, headers=_AUTH
        )

    assert response.status_code == 400


def test_erro_do_replay_vira_a_resposta_http(debug_ligado, monkeypatch):
    from src.workflow.debug_replay import ReplayError

    async def fake_execute_single_node(*args, **kwargs):
        raise ReplayError(404, "Esse turno não existe nesta conversa de debug.")

    monkeypatch.setattr(
        "src.api.routes.debug.execute_single_node", fake_execute_single_node
    )

    with _client() as client:
        response = client.post(
            "/debug/chat", json={**_BODY, "custom": _CUSTOM}, headers=_AUTH
        )

    assert response.status_code == 404
    assert "turno" in response.json()["detail"]


def test_resposta_traz_o_indice_do_turno_executado(debug_ligado, monkeypatch):
    async def fake_execute_turn(thread_id, message, workflow, **kwargs):
        return {**_estado_final(), "messenger_conversation_id": None}

    async def fake_count_turns(workflow, thread_id):
        return 3

    monkeypatch.setattr("src.api.routes.debug.execute_turn", fake_execute_turn)
    monkeypatch.setattr("src.api.routes.debug.count_turns", fake_count_turns)

    with _client() as client:
        response = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert response.json()["debug"]["turn"] == 2


def test_falha_no_turno_tambem_traz_o_indice_do_turno(debug_ligado, monkeypatch):
    async def fake_execute_turn(*args, **kwargs):
        raise RuntimeError("falhou")

    async def fake_count_turns(workflow, thread_id):
        return 1

    monkeypatch.setattr("src.api.routes.debug.execute_turn", fake_execute_turn)
    monkeypatch.setattr("src.api.routes.debug.count_turns", fake_count_turns)

    with _client() as client:
        response = client.post("/debug/chat", json=_BODY, headers=_AUTH)

    assert response.status_code == 500
    assert response.json()["debug"]["turn"] == 0


def test_execucao_personalizada_deixa_log_de_auditoria_sem_conteudo(
    debug_ligado, monkeypatch, caplog
):
    async def fake_execute_single_node(*args, **kwargs):
        return {}, ("router",), 1

    monkeypatch.setattr(
        "src.api.routes.debug.execute_single_node", fake_execute_single_node
    )

    with caplog.at_level("INFO", logger="src.api.routes.debug"), _client() as client:
        client.post("/debug/chat", json={**_BODY, "custom": _CUSTOM}, headers=_AUTH)

    linha = next(
        r.getMessage() for r in caplog.records if "personalizada" in r.getMessage()
    )
    assert ADMIN_SUB in linha
    assert "router" in linha
    assert "NOVO PROMPT" not in linha
