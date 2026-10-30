import asyncio
from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage

import src.workflow.runner as runner


def _workflow():
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="oi", additional_kwargs={})]}
    )
    return workflow


def test_execute_turn_sem_persistir_so_passa_pelo_grafo(monkeypatch):
    workflow = _workflow()
    criar_conversa_chatbot = AsyncMock()
    enviar_mensagem_usuario = AsyncMock()
    enviar_mensagem_chatbot = AsyncMock()
    get_user_memory = AsyncMock()
    agendar = Mock()
    monkeypatch.setattr(runner, "criar_conversa_chatbot", criar_conversa_chatbot)
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", enviar_mensagem_usuario)
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", enviar_mensagem_chatbot)
    monkeypatch.setattr(runner, "get_user_memory", get_user_memory)
    monkeypatch.setattr(runner, "_agendar_atualizacao_memoria", agendar)
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="user-1"))
    coletor = object()

    resultado = asyncio.run(
        runner.execute_turn(
            "debug:thread",
            "texto",
            workflow,
            user_token="t",
            persist=False,
            extra_callbacks=[coletor],
        )
    )

    criar_conversa_chatbot.assert_not_awaited()
    enviar_mensagem_usuario.assert_not_awaited()
    enviar_mensagem_chatbot.assert_not_awaited()
    get_user_memory.assert_not_awaited()
    agendar.assert_not_called()
    assert resultado["messages"][0].content == "oi"
    config_usado = workflow.ainvoke.await_args.kwargs["config"]
    assert config_usado["callbacks"] == [coletor]
    assert config_usado["configurable"] == {"thread_id": "debug:thread"}
    assert workflow.ainvoke.await_args.args[0]["user_memory"] == ""
