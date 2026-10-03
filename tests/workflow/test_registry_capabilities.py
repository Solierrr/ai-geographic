from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from src.core.travel.models import Coordinate, ResolvedPlace
from src.infra.external.google_registry.errors import (
    RegistryUnavailableError,
    SolarCoverageUnavailableError,
)
from src.infra.external.google_registry.geo import TimezoneInfo
from src.infra.external.google_registry.models import SolarViability
from src.workflow.nodes import (
    input_guardrail_node,
    judge_node,
    location_node,
    orchestrator_node,
    output_guardrail_node,
    solar_node,
    timezone_node,
)


def _place() -> ResolvedPlace:
    return ResolvedPlace(
        label="Av. Paulista, 1000",
        address="Av. Paulista, 1000, São Paulo - SP",
        coordinate=Coordinate(latitude=-23.5, longitude=-46.6),
        place_id="p1",
    )


def _viability() -> SolarViability:
    return SolarViability(
        imagery_date="2024-03-05",
        usable_roof_area_m2=42.5,
        max_panel_count=20,
        annual_sunshine_hours=1800,
        carbon_offset_factor_kg_mwh=400,
        roof_segments=[
            {"pitch_degrees": 20, "azimuth_degrees": 180, "area_m2": 42.5}
        ],
        panel_capacity_watts=400,
        panel_configs=[{"panels_count": 10, "yearly_energy_dc_kwh": 6200}],
    )


def _mock_intent(monkeypatch, content: str):
    model = Mock()
    model.invoke.return_value = SimpleNamespace(content=content)
    gemini = Mock()
    gemini.with_fallbacks.return_value = model
    monkeypatch.setattr(orchestrator_node, "llm_gemini", Mock(return_value=gemini))
    monkeypatch.setattr(orchestrator_node, "llm_groq", Mock())


def test_solar_without_location_asks_for_address(monkeypatch):
    _mock_intent(
        monkeypatch,
        '{"intent":"solar","response_language":"pt-BR","destination":null}',
    )
    result = orchestrator_node.orchestrator_node(
        {"messages": [HumanMessage(content="Qual é o potencial solar?")], "turn_agents": []}
    )
    assert result["flow_status"] == "respond"
    assert "endereço" in result["messages"][0].content


@pytest.mark.asyncio
async def test_solar_resolves_address_before_query(monkeypatch):
    place = _place()
    search = AsyncMock(return_value=[place])
    monkeypatch.setattr(location_node, "search_places", search)
    located = await location_node.resolve_locations_node(
        {
            "trip_request": {
                "intent": "solar",
                "destination": "Av Paulista 1000",
                "response_language": "pt-BR",
            },
            "turn_agents": [],
        }
    )
    assert located["flow_status"] == "solar"
    search.assert_awaited_once()

    query = AsyncMock(return_value=_viability())
    monkeypatch.setattr(solar_node, "get_roof_viability", query)
    result = await solar_node.solar_node({**located, "turn_agents": []})
    query.assert_awaited_once_with(place.coordinate)
    assert result["solar_result"]["max_panel_count"] == 20


@pytest.mark.asyncio
async def test_solar_response_only_uses_received_values(monkeypatch):
    monkeypatch.setattr(solar_node, "get_roof_viability", AsyncMock(return_value=_viability()))
    result = await solar_node.solar_node(
        {"resolved_destination": _place().model_dump(mode="json"), "turn_agents": []}
    )
    answer = result["messages"][0].content
    assert "42,5 m²" in answer
    assert "20 painéis" in answer
    assert "6.200,0 kWh/ano" in answer
    assert "não substituem" in answer
    assert "economia" not in answer.casefold()


@pytest.mark.asyncio
async def test_solar_response_keeps_user_language(monkeypatch):
    monkeypatch.setattr(solar_node, "get_roof_viability", AsyncMock(return_value=_viability()))
    result = await solar_node.solar_node(
        {
            "resolved_destination": _place().model_dump(mode="json"),
            "trip_request": {"response_language": "en"},
            "turn_agents": [],
        }
    )
    assert "provider estimates" in result["messages"][0].content
    assert "não substituem" not in result["messages"][0].content


@pytest.mark.asyncio
async def test_solar_distinguishes_no_coverage_and_temporary_failure(monkeypatch):
    state = {"resolved_destination": _place().model_dump(mode="json"), "turn_agents": []}
    monkeypatch.setattr(
        solar_node,
        "get_roof_viability",
        AsyncMock(side_effect=SolarCoverageUnavailableError("none")),
    )
    no_coverage = await solar_node.solar_node(state)
    assert no_coverage["provider_issue"] == "solar_coverage_unavailable"
    assert "cobertura" in no_coverage["messages"][0].content

    monkeypatch.setattr(
        solar_node,
        "get_roof_viability",
        AsyncMock(side_effect=RegistryUnavailableError("down")),
    )
    unavailable = await solar_node.solar_node(state)
    assert unavailable["provider_issue"] == "unavailable"
    assert "temporariamente" in unavailable["messages"][0].content


@pytest.mark.asyncio
async def test_timezone_node_uses_internal_zoneinfo(monkeypatch):
    monkeypatch.setattr(
        timezone_node,
        "get_timezone",
        AsyncMock(
            return_value=TimezoneInfo(
                zone=ZoneInfo("America/Sao_Paulo"), utc_offset_seconds=-10800
            )
        ),
    )
    result = await timezone_node.timezone_node(
        {"resolved_destination": _place().model_dump(mode="json"), "turn_agents": []}
    )
    assert result["timezone_result"]["timezone_id"] == "America/Sao_Paulo"
    assert "UTC-03:00" in result["messages"][0].content


@pytest.mark.asyncio
async def test_current_location_is_only_used_when_explicitly_present(monkeypatch):
    search = AsyncMock()
    monkeypatch.setattr(location_node, "search_places", search)
    request = {
        "intent": "solar",
        "destination": "aqui",
        "response_language": "pt-BR",
    }
    missing = await location_node.resolve_locations_node(
        {"trip_request": request, "turn_agents": []}
    )
    assert missing["flow_status"] == "respond"
    assert "endereço" in missing["messages"][0].content
    search.assert_not_awaited()

    present = await location_node.resolve_locations_node(
        {
            "trip_request": request,
            "current_location": {"latitude": -23.5, "longitude": -46.6},
            "turn_agents": [],
        }
    )
    assert present["flow_status"] == "solar"
    assert present["resolved_destination"]["place_id"] is None


@pytest.mark.asyncio
async def test_graph_runs_solar_flow_and_keeps_provider_data_ephemeral(monkeypatch):
    from src.workflow.graph.graph import graph

    approved_input = Mock()
    approved_input.invoke.return_value = AIMessage(
        content="CATEGORIA: APROVADO\nJUSTIFICATIVA: análise solar"
    )
    monkeypatch.setattr(
        input_guardrail_node, "llm_groq", Mock(return_value=approved_input)
    )
    _mock_intent(
        monkeypatch,
        '{"intent":"solar","response_language":"pt-BR",'
        '"destination":"Av Paulista 1000"}',
    )
    monkeypatch.setattr(location_node, "search_places", AsyncMock(return_value=[_place()]))
    monkeypatch.setattr(
        solar_node, "get_roof_viability", AsyncMock(return_value=_viability())
    )

    def review(messages, config=None):
        prompt = messages[0].content
        text = prompt.split("Resposta para revisar:\n\n", 1)[1].split(
            "Responda EXATAMENTE", 1
        )[0].strip()
        return AIMessage(content=f"STATUS: APROVADO\nRESPOSTA: {text}")

    review_model = Mock()
    review_model.invoke.side_effect = review
    monkeypatch.setattr(
        output_guardrail_node, "llm_groq", Mock(return_value=review_model)
    )
    judge_model = Mock()
    judge_model.invoke.return_value = AIMessage(
        content="STATUS: APROVADO\nJUSTIFICATIVA: números conferidos"
    )
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=judge_model))

    workflow = graph.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "solar-flow"}}
    final = await workflow.ainvoke(
        {
            "messages": [HumanMessage(content="Qual o potencial solar da Av Paulista 1000?")],
            "turn_agents": [],
            "judge_retries": 0,
        },
        config=config,
    )

    assert final["judge_status"] == "approved"
    assert final["solar_result"]["max_panel_count"] == 20
    assert final["messages"][-1].additional_kwargs["specialists_used"] == ["solar"]
    stored = (await workflow.aget_state(config)).values
    assert "solar_result" not in stored
    assert "resolved_destination" not in stored
