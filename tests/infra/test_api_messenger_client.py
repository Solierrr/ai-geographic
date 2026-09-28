import json

import pytest
import respx
from httpx import Response

from src.infra.api_messenger import client


@pytest.mark.asyncio
@respx.mock
async def test_criar_conversa_usa_token_do_usuario(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "LOCAL")

    criar_route = respx.post(
        "http://api-messenger/messaging/conversations/chatbot-conversations"
    ).mock(return_value=Response(200, json={"id": "conv-1"}))

    conversation_id = await client.criar_conversa_chatbot(
        "lead", {"empresa": "ExemploCorp"}, user_token="token-do-usuario"
    )

    assert conversation_id == "conv-1"
    assert (
        criar_route.calls.last.request.headers["Authorization"]
        == "Bearer token-do-usuario"
    )


@pytest.mark.asyncio
@respx.mock
async def test_criar_conversa_manda_environment_no_corpo(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "QA")

    criar_route = respx.post(
        "http://api-messenger/messaging/conversations/chatbot-conversations"
    ).mock(return_value=Response(200, json={"id": "conv-1"}))

    await client.criar_conversa_chatbot("lead", {}, user_token="token-do-usuario")

    corpo = json.loads(criar_route.calls.last.request.content)
    assert corpo["environment"] == "QA"


@pytest.mark.asyncio
@respx.mock
async def test_enviar_mensagem_chatbot_nao_manda_header_de_autenticacao(monkeypatch):
    """/internal/** não exige mais auth de aplicação — confirma que a
    requisição não carrega Authorization nenhum."""
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "LOCAL")

    mensagem_route = respx.post("http://api-messenger/internal/messages").mock(
        return_value=Response(200, json={})
    )

    await client.enviar_mensagem_chatbot("conv-1", "ola", {"turnId": "t-1"})

    assert mensagem_route.called
    assert "Authorization" not in mensagem_route.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_enviar_mensagem_chatbot_manda_environment_e_metadata_camel_case(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "PROD")

    mensagem_route = respx.post("http://api-messenger/internal/messages").mock(
        return_value=Response(200, json={})
    )

    metadata = {
        "turnId": "t-1",
        "contentAnonymized": True,
        "specialistsUsed": [],
        "workflowSteps": [],
    }
    await client.enviar_mensagem_chatbot("conv-1", "ola", metadata)

    corpo = json.loads(mensagem_route.calls.last.request.content)
    assert corpo["environment"] == "PROD"
    assert corpo["metadata"] == metadata


@pytest.mark.asyncio
@respx.mock
async def test_enviar_observabilidade_nao_manda_header_de_autenticacao(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "LOCAL")

    obs_route = respx.post("http://api-messenger/internal/observability").mock(
        return_value=Response(200, json={})
    )

    await client.enviar_observabilidade({"node": "router", "status": "ok"})

    assert obs_route.called
    assert "Authorization" not in obs_route.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_enviar_mensagem_usuario_usa_endpoint_e_jwt_do_usuario(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "QA")

    mensagem_route = respx.post("http://api-messenger/messaging/messages").mock(
        return_value=Response(201, json={})
    )

    await client.enviar_mensagem_usuario("conv-1", "ola", "token-do-usuario")

    request = mensagem_route.calls.last.request
    corpo = json.loads(request.content)
    assert request.headers["Authorization"] == "Bearer token-do-usuario"
    assert corpo == {
        "conversationId": "conv-1",
        "messageType": "USER_TO_CHATBOT",
        "role": "user",
        "content": "ola",
        "environment": "QA",
    }
