from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base.system_prompt import (
    SYSTEM_CORE_COMMUNICATION,
    SYSTEM_CORE_SECURITY,
)
from src.agents.specialist.router.router_prompt import ROUTER_AGENT
from src.workflow.nodes import router_node


def _mock_llm(route, direct_response=""):
    llm = Mock()
    llm.invoke.return_value = AIMessage(
        content=f"ROTA: {route if route is not None else 'None'}\nRESPOSTA_DIRETA: {direct_response}"
    )
    return llm


def test_router_routes_to_valid_specialist(monkeypatch):
    llm = _mock_llm("example_specialist")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))
    result = router_node.router_node(
        {"messages": [HumanMessage(content="Preciso de ajuda")]}
    )
    assert result == {"route": "example_specialist", "turn_agents": ["router"]}
    messages = llm.invoke.call_args.args[0]
    assert isinstance(messages[0], SystemMessage)
    assert SYSTEM_CORE_SECURITY.strip() in messages[0].content
    assert SYSTEM_CORE_COMMUNICATION.strip() in messages[0].content
    assert ROUTER_AGENT.strip() in messages[0].content
    assert "ROTA:" in messages[1].content
    llm.with_structured_output.assert_not_called()


def test_router_routes_to_second_specialist(monkeypatch):
    llm = _mock_llm("example_specialist_two")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    result = router_node.router_node(
        {"messages": [HumanMessage(content="Preciso de outra coisa")]}
    )

    assert result == {"route": "example_specialist_two", "turn_agents": ["router"]}

    llm = _mock_llm("orchestrator")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))
    result = router_node.router_node(
        {
            "messages": [HumanMessage(content="Ja respondeu")],
            "turn_agents": ["example_specialist"],
        }
    )
    assert result["route"] == "orchestrator"


def test_router_returns_direct_response(monkeypatch):
    llm = _mock_llm(None, "Posso ajudar com essa informacao diretamente.")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))
    result = router_node.router_node({"messages": [HumanMessage(content="Uma duvida qualquer")]})
    assert result["route"] == "end"
    assert result["messages"][0].content == "Posso ajudar com essa informacao diretamente."


def test_router_short_circuits_at_specialist_limit(monkeypatch):
    llm = Mock()
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(router_node.config, "MAX_SPECIALISTS_PER_REQUEST", 1)
    result = router_node.router_node(
        {
            "messages": [HumanMessage(content="Mais uma")],
            "turn_agents": ["example_specialist"],
        }
    )
    assert result["route"] == "orchestrator"
    llm.invoke.assert_not_called()


def test_router_only_offers_unused_routes(monkeypatch):
    llm = _mock_llm("example_specialist_two")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    router_node.router_node(
        {
            "messages": [HumanMessage(content="Preciso de ajuda")],
            "summary": "O usuario ja recebeu uma resposta de um especialista.",
            "turn_agents": ["example_specialist"],
        }
    )

    messages = llm.invoke.call_args.args[0]
    assert (
        "Rotas disponiveis nesta solicitacao: example_specialist_two."
        in messages[1].content
    )
    assert "Resumo" in messages[2].content


def test_router_falls_back_for_invalid_route(monkeypatch):
    llm = _mock_llm("rota_inventada")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))
    result = router_node.router_node({"messages": [HumanMessage(content="Ajuda")]})
    assert result == {"route": "orchestrator", "turn_agents": ["router_invalid_route"]}


def test_router_falls_back_for_malformed_response(monkeypatch):
    llm = Mock()
    llm.invoke.return_value = AIMessage(content="Escolha example_specialist")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))
    result = router_node.router_node({"messages": [HumanMessage(content="Ajuda")]})
    assert result == {"route": "orchestrator", "turn_agents": ["router_invalid_response"]}


def test_router_falls_back_when_direct_response_is_empty(monkeypatch):
    llm = _mock_llm(None)
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    result = router_node.router_node({"messages": [HumanMessage(content="Ajuda")]})

    assert result == {"route": "orchestrator", "turn_agents": ["router_invalid_response"]}
