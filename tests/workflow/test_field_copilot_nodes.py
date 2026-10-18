import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from ai_lib.a2a import DelegationError, DelegationResult
from langchain_core.messages import AIMessage, HumanMessage

from src.core.security.request_context import current_user_token
from src.workflow.nodes import (
    field_conditions_node,
    product_advisor_node,
    route_planner_node,
)

STATE = {"messages": [HumanMessage(content="Vale ir ao cliente em Campinas amanhã?")]}


def _tool(nome: str) -> Mock:
    tool = Mock()
    tool.name = nome
    return tool


def _agent(texto: str) -> Mock:
    agent = Mock()
    agent.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content=texto)]})
    return agent


@pytest.mark.parametrize(
    ("module", "node", "prompt", "tools", "agent_name"),
    [
        (
            route_planner_node,
            route_planner_node.route_planner_node,
            "ROUTE_PLANNER_AGENT",
            ("resolve_names", "search_places", "compute_routes"),
            "route_planner",
        ),
        (
            field_conditions_node,
            field_conditions_node.field_conditions_node,
            "FIELD_CONDITIONS_AGENT",
            ("resolve_names", "lookup_weather"),
            "field_conditions",
        ),
    ],
)
def test_especialista_de_maps_usa_so_as_tools_do_dominio(
    monkeypatch, module, node, prompt, tools, agent_name
):
    tools_do_maps = [_tool(nome) for nome in tools]
    get_tools = AsyncMock(return_value=tools_do_maps)
    monkeypatch.setattr(module, "get_mcp_tools_by_name", get_tools)
    agent = _agent("Vale ir: sem chuva prevista.")
    build_agent = Mock(return_value=agent)
    monkeypatch.setattr(module, "build_agent", build_agent)

    result = asyncio.run(node(STATE))

    get_tools.assert_awaited_once_with(*tools)
    build_agent.assert_called_once_with(getattr(module, prompt), tools=tools_do_maps)
    assert result["messages"][0].content == "Vale ir: sem chuva prevista."
    assert result["turn_agents"] == [agent_name]


@pytest.mark.parametrize(
    ("module", "node"),
    [
        (route_planner_node, route_planner_node.route_planner_node),
        (field_conditions_node, field_conditions_node.field_conditions_node),
    ],
)
def test_maps_indisponivel_responde_com_aviso_sem_quebrar(monkeypatch, module, node):
    monkeypatch.setattr(
        module,
        "get_mcp_tools_by_name",
        AsyncMock(side_effect=RuntimeError("sem chave")),
    )
    build_agent = Mock()
    monkeypatch.setattr(module, "build_agent", build_agent)

    result = asyncio.run(node(STATE))

    assert "Não consegui consultar" in result["messages"][0].content
    build_agent.assert_not_called()


def test_prompt_de_condicoes_avisa_que_nao_ha_irradiacao():
    from src.agents.specialist.field_conditions.field_conditions_prompt import (
        FIELD_CONDITIONS_AGENT,
    )

    assert "NÃO traz irradiação solar" in FIELD_CONDITIONS_AGENT


@pytest.fixture
def token():
    valor = current_user_token.set("jwt-do-profissional")
    yield "jwt-do-profissional"
    current_user_token.reset(valor)


def _delegate(monkeypatch, outcome="completed", text="Recomendo a placa X."):
    mock = AsyncMock(
        return_value=DelegationResult(
            outcome=outcome, text=text, task_id="t1", context_id="conversa-1"
        )
    )
    monkeypatch.setattr(product_advisor_node, "delegate", mock)
    return mock


def test_produtos_delega_ao_assistente_como_profissional(monkeypatch, token):
    mock = _delegate(monkeypatch)
    config = {"configurable": {"thread_id": "conversa-1"}}
    state = {"messages": [HumanMessage(content="Qual placa serve a esse telhado?")]}

    result = asyncio.run(product_advisor_node.product_advisor_node(state, config))

    mock.assert_awaited_once_with(
        product_advisor_node.settings.A2A_ASSISTANT_URL,
        "Qual placa serve a esse telhado?",
        token=token,
        persona="profissional",
        context_id="conversa-1",
    )
    assert result["messages"][0].content == "Recomendo a placa X."
    assert result["turn_agents"] == ["product_advisor"]


def test_produtos_sem_token_nao_delega(monkeypatch):
    mock = _delegate(monkeypatch)

    result = asyncio.run(product_advisor_node.product_advisor_node(STATE))

    mock.assert_not_awaited()
    assert "autenticado" in result["messages"][0].content


def test_produtos_com_assistente_fora_do_ar_responde_com_aviso(monkeypatch, token):
    monkeypatch.setattr(
        product_advisor_node, "delegate", AsyncMock(side_effect=DelegationError("fora"))
    )

    result = asyncio.run(product_advisor_node.product_advisor_node(STATE))

    assert "Não consegui falar" in result["messages"][0].content


@pytest.mark.parametrize("outcome", ["failed", "rejected", "canceled", "unknown"])
def test_produtos_com_desfecho_sem_sucesso_responde_com_aviso(
    monkeypatch, token, outcome
):
    _delegate(monkeypatch, outcome=outcome, text="detalhe interno")

    result = asyncio.run(product_advisor_node.product_advisor_node(STATE))

    assert "Não consegui falar" in result["messages"][0].content
