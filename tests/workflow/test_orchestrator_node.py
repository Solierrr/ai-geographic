from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base.system_prompt import SYSTEM_CORE_COMMUNICATION, SYSTEM_CORE_SECURITY
from src.agents.specialist.orchestrator.orchestrator_prompt import ORCHESTRATOR_AGENT
import src.workflow.nodes.orchestrator_node as orchestrator_node


def test_orchestrator_node_uses_prompt_and_fallback(monkeypatch):
    llm_com_fallback = Mock()
    llm_com_fallback.invoke.return_value = SimpleNamespace(content="Resposta final consolidada")
    monkeypatch.setattr(orchestrator_node, "llm_chain", Mock(return_value=llm_com_fallback))

    resultado = orchestrator_node.orchestrator_node(
        {"messages": [HumanMessage(content="Olá")], "turn_agents": ["example_specialist"]}
    )

    assert resultado["turn_agents"] == ["example_specialist", "orchestrator"]
    assert resultado["messages"][0].content == "Resposta final consolidada"
    mensagens = llm_com_fallback.invoke.call_args.args[0]
    assert isinstance(mensagens[0], SystemMessage)
    assert SYSTEM_CORE_SECURITY.strip() in mensagens[0].content
    assert SYSTEM_CORE_COMMUNICATION.strip() in mensagens[0].content
    assert ORCHESTRATOR_AGENT.strip() in mensagens[0].content
    assert isinstance(mensagens[1], HumanMessage)


def test_orchestrator_node_keeps_summary_in_context(monkeypatch):
    llm_com_fallback = Mock()
    llm_com_fallback.invoke.return_value = SimpleNamespace(content="Resposta")
    monkeypatch.setattr(orchestrator_node, "llm_chain", Mock(return_value=llm_com_fallback))

    orchestrator_node.orchestrator_node(
        {
            "messages": [HumanMessage(content="Qual a garantia?")],
            "summary": "O usuário quer informações sobre painéis solares.",
        }
    )

    mensagens = llm_com_fallback.invoke.call_args.args[0]
    assert "Resumo" in mensagens[1].content
    assert isinstance(mensagens[2], HumanMessage)
