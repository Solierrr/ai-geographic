import asyncio
from unittest.mock import AsyncMock

from src.agents.base import base_memory


def test_get_recent_history_limita_mensagens():
    resultado = base_memory.get_recent_history({"messages": [1, 2, 3]}, limit=2)

    assert resultado == [2, 3]


def test_log_user_interaction_envia_com_jwt_do_usuario(monkeypatch):
    enviar_mensagem_usuario = AsyncMock()
    monkeypatch.setattr(base_memory, "enviar_mensagem_usuario", enviar_mensagem_usuario)

    asyncio.run(base_memory.log_user_interaction("conv-1", "ola", "token-do-usuario"))

    enviar_mensagem_usuario.assert_awaited_once_with(
        "conv-1", "ola", "token-do-usuario"
    )


def test_log_assistant_interaction_envia_para_api_messenger(monkeypatch):
    enviar_mensagem_chatbot = AsyncMock()
    monkeypatch.setattr(base_memory, "enviar_mensagem_chatbot", enviar_mensagem_chatbot)

    asyncio.run(
        base_memory.log_assistant_interaction(
            "conv-1",
            "ola",
            metadata={"turnId": "t-1"},
        )
    )

    enviar_mensagem_chatbot.assert_awaited_once_with(
        "conv-1",
        "ola",
        {"turnId": "t-1"},
    )


def test_log_assistant_interaction_sem_metadata_extra(monkeypatch):
    enviar_mensagem_chatbot = AsyncMock()
    monkeypatch.setattr(base_memory, "enviar_mensagem_chatbot", enviar_mensagem_chatbot)

    asyncio.run(base_memory.log_assistant_interaction("conv-1", "oi"))

    enviar_mensagem_chatbot.assert_awaited_once_with(
        "conv-1",
        "oi",
        None,
    )
