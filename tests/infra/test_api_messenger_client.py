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
    route = respx.post(
        "http://api-messenger/messaging/conversations/chatbot-conversations"
    ).mock(return_value=Response(200, json={"id": "conv-1"}))
    conversation_id = await client.criar_conversa_chatbot(
        "lead", {"empresa": "ExemploCorp"}, user_token="token-do-usuario"
    )
    assert conversation_id == "conv-1"
    assert (
        route.calls.last.request.headers["Authorization"] == "Bearer token-do-usuario"
    )


@pytest.mark.asyncio
@respx.mock
async def test_criar_conversa_manda_environment_no_corpo(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "QA")
    route = respx.post(
        "http://api-messenger/messaging/conversations/chatbot-conversations"
    ).mock(return_value=Response(200, json={"id": "conv-1"}))
    await client.criar_conversa_chatbot("lead", {}, user_token="token-do-usuario")
    assert json.loads(route.calls.last.request.content)["environment"] == "QA"


@pytest.mark.asyncio
@respx.mock
async def test_enviar_mensagem_chatbot_usa_token_de_servico(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "LOCAL")
    monkeypatch.setattr(client.settings, "SERVICE_CLIENT_SECRET", "segredo")
    monkeypatch.setattr(client, "_service_access_token", None)
    token_route = respx.post("http://api-messenger/internal/service-tokens").mock(
        return_value=Response(200, json={"accessToken": "token-m2m", "expiresIn": 300})
    )
    mensagem_route = respx.post("http://api-messenger/internal/messages").mock(
        return_value=Response(200, json={})
    )
    await client.enviar_mensagem_chatbot("conv-1", "ola", {"turnId": "t-1"})
    assert token_route.called
    assert (
        mensagem_route.calls.last.request.headers["Authorization"] == "Bearer token-m2m"
    )


@pytest.mark.asyncio
@respx.mock
async def test_enviar_mensagem_chatbot_manda_environment_e_metadata(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "PROD")
    monkeypatch.setattr(client, "_service_access_token", "token-em-cache")
    monkeypatch.setattr(client, "_service_token_expires_at", float("inf"))
    route = respx.post("http://api-messenger/internal/messages").mock(
        return_value=Response(200, json={})
    )
    metadata = {
        "turnId": "t-1",
        "contentAnonymized": True,
        "specialistsUsed": [],
        "workflowSteps": [],
    }
    await client.enviar_mensagem_chatbot("conv-1", "ola", metadata)
    corpo = json.loads(route.calls.last.request.content)
    assert corpo["environment"] == "PROD"
    assert corpo["metadata"] == metadata


@pytest.mark.asyncio
@respx.mock
async def test_enviar_observabilidade_usa_token_de_servico_em_cache(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "LOCAL")
    monkeypatch.setattr(client, "_service_access_token", "token-em-cache")
    monkeypatch.setattr(client, "_service_token_expires_at", float("inf"))
    route = respx.post("http://api-messenger/internal/observability").mock(
        return_value=Response(200, json={})
    )
    await client.enviar_observabilidade({"node": "orchestrator", "status": "ok"})
    assert route.calls.last.request.headers["Authorization"] == "Bearer token-em-cache"


@pytest.mark.asyncio
@respx.mock
async def test_enviar_mensagem_usuario_usa_endpoint_e_jwt_do_usuario(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "QA")
    route = respx.post("http://api-messenger/messaging/messages").mock(
        return_value=Response(201, json={})
    )
    await client.enviar_mensagem_usuario("conv-1", "ola", "token-do-usuario")
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer token-do-usuario"
    assert json.loads(request.content) == {
        "conversationId": "conv-1",
        "messageType": "USER_TO_CHATBOT",
        "role": "user",
        "content": "ola",
        "environment": "QA",
    }
