from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.base.system_prompt import (
    SYSTEM_CORE_COMMUNICATION,
    SYSTEM_CORE_SECURITY,
)
from src.agents.specialist.orchestrator.orchestrator_prompt import ORCHESTRATOR_AGENT
from src.workflow.nodes import orchestrator_node


def test_orchestrator_node_uses_prompt_and_fallback(monkeypatch):
    gemini = Mock()
    groq = Mock()
    llm_com_fallback = Mock()
    llm_com_fallback.invoke.return_value = SimpleNamespace(
        content='{"intent":"out_of_scope","origin":null,"destination":null,"mode":null,"time_kind":"now","local_time":null}'
    )
    gemini.with_fallbacks.return_value = llm_com_fallback
    monkeypatch.setattr(orchestrator_node, "llm_gemini", Mock(return_value=gemini))
    monkeypatch.setattr(orchestrator_node, "llm_groq", Mock(return_value=groq))

    resultado = orchestrator_node.orchestrator_node(
        {"messages": [HumanMessage(content="Olá")], "turn_agents": ["input_guardrail_approved"]}
    )

    assert resultado["turn_agents"] == ["input_guardrail_approved", "orchestrator"]
    assert resultado["intent"] == "out_of_scope"
    assert "deslocamento" in resultado["messages"][0].content
    gemini.with_fallbacks.assert_called_once_with([groq])
    mensagens = llm_com_fallback.invoke.call_args.args[0]
    assert isinstance(mensagens[0], SystemMessage)
    assert SYSTEM_CORE_SECURITY.strip() in mensagens[0].content
    assert SYSTEM_CORE_COMMUNICATION.strip() in mensagens[0].content
    assert ORCHESTRATOR_AGENT.strip() in mensagens[0].content
    assert isinstance(mensagens[2], HumanMessage)


def test_orchestrator_node_keeps_summary_in_context(monkeypatch):
    gemini = Mock()
    groq = Mock()
    llm_com_fallback = Mock()
    llm_com_fallback.invoke.return_value = SimpleNamespace(content="Resposta")
    gemini.with_fallbacks.return_value = llm_com_fallback
    monkeypatch.setattr(orchestrator_node, "llm_gemini", Mock(return_value=gemini))
    monkeypatch.setattr(orchestrator_node, "llm_groq", Mock(return_value=groq))

    orchestrator_node.orchestrator_node(
        {
            "messages": [HumanMessage(content="Qual a garantia?")],
            "summary": "O usuário quer informações sobre painéis solares.",
        }
    )

    mensagens = llm_com_fallback.invoke.call_args.args[0]
    assert "Resumo" in mensagens[2].content
    assert isinstance(mensagens[3], HumanMessage)
