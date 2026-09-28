from langchain_core.messages import HumanMessage, SystemMessage

from src.workflow.nodes.context import messages_with_summary


def test_messages_with_summary_sem_memoria_nem_resumo_retorna_so_mensagens():
    state = {"messages": [HumanMessage(content="oi")]}

    resultado = messages_with_summary(state)

    assert resultado == [HumanMessage(content="oi")]


def test_messages_with_summary_injeta_memoria_do_usuario():
    state = {
        "messages": [HumanMessage(content="oi")],
        "user_memory": "- mora em SP\n- é instalador",
    }

    resultado = messages_with_summary(state)

    assert len(resultado) == 2
    assert isinstance(resultado[0], SystemMessage)
    assert "mora em SP" in resultado[0].content
    assert resultado[1] == HumanMessage(content="oi")


def test_messages_with_summary_injeta_memoria_e_resumo_nessa_ordem():
    state = {
        "messages": [HumanMessage(content="oi")],
        "user_memory": "- mora em SP",
        "summary": "Conversa anterior sobre orçamento",
    }

    resultado = messages_with_summary(state)

    assert len(resultado) == 3
    assert "mora em SP" in resultado[0].content
    assert "Conversa anterior sobre orçamento" in resultado[1].content
    assert resultado[2] == HumanMessage(content="oi")
