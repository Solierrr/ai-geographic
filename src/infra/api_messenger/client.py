"""Cliente HTTP do api-messenger."""

import asyncio
import time

import httpx

from src.core.config.settings import settings

_service_access_token: str | None = None
_service_token_expires_at = 0.0
_service_token_lock = asyncio.Lock()


async def _obter_token_servico(client: httpx.AsyncClient) -> str:
    """Obtém e reutiliza o token M2M exigido pelos endpoints /internal/**."""
    global _service_access_token, _service_token_expires_at

    if _service_access_token and time.monotonic() < _service_token_expires_at:
        return _service_access_token
    if not settings.SERVICE_CLIENT_SECRET:
        raise RuntimeError("SERVICE_CLIENT_SECRET não configurado")

    async with _service_token_lock:
        if _service_access_token and time.monotonic() < _service_token_expires_at:
            return _service_access_token
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/internal/service-tokens",
            json={"clientSecret": settings.SERVICE_CLIENT_SECRET},
        )
        resp.raise_for_status()
        token_data = resp.json()
        _service_access_token = token_data["accessToken"]
        ttl = max(int(token_data.get("expiresIn", 300)) - 30, 1)
        _service_token_expires_at = time.monotonic() + ttl
        return _service_access_token


async def criar_conversa_chatbot(
    user_type: str, user_details: dict, user_token: str
) -> str:
    """Cria a conversa com o JWT do usuário real."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/messaging/conversations/chatbot-conversations",
            json={
                "userType": user_type,
                "userDetails": user_details,
                "environment": settings.ENVIRONMENT,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def enviar_mensagem_chatbot(
    conversation_id: str, content: str, metadata: dict | None = None
) -> None:
    """Registra a resposta do assistente."""
    async with httpx.AsyncClient() as client:
        token = await _obter_token_servico(client)
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/internal/messages",
            json={
                "conversationId": conversation_id,
                "content": content,
                "metadata": metadata,
                "environment": settings.ENVIRONMENT,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()


async def enviar_observabilidade(payload: dict) -> None:
    async with httpx.AsyncClient() as client:
        token = await _obter_token_servico(client)
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/internal/observability",
            json={**payload, "environment": settings.ENVIRONMENT},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()


async def enviar_mensagem_usuario(
    conversation_id: str, content: str, user_token: str
) -> None:
    """Registra a mensagem do usuário usando seu próprio JWT."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/messaging/messages",
            json={
                "conversationId": conversation_id,
                "messageType": "USER_TO_CHATBOT",
                "role": "user",
                "content": content,
                "environment": settings.ENVIRONMENT,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        resp.raise_for_status()
