"""Cliente HTTP do api-messenger."""

import httpx

from src.core.config.settings import settings


async def criar_conversa_chatbot(user_type: str, user_details: dict, user_token: str) -> str:
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
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/internal/messages",
            json={
                "conversationId": conversation_id,
                "content": content,
                "metadata": metadata,
                "environment": settings.ENVIRONMENT,
            },
        )
        resp.raise_for_status()


async def enviar_observabilidade(payload: dict) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/internal/observability",
            json={**payload, "environment": settings.ENVIRONMENT},
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
