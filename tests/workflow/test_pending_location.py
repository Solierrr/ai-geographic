from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from src.core.travel.models import Coordinate, ResolvedPlace
from src.workflow.nodes import input_guardrail_node, location_node, orchestrator_node
from src.workflow.state import GraphState


@pytest.mark.asyncio
async def test_choice_from_previous_turn_resolves_place_id(monkeypatch):
    origin = ResolvedPlace(
        label="Centro", address="Centro, São Paulo", place_id="origin-1",
        coordinate=Coordinate(latitude=-23.55, longitude=-46.63),
    )
    destination = ResolvedPlace(
        label="Parque", address="Parque, São Paulo", place_id="destination-1",
        coordinate=Coordinate(latitude=-23.58, longitude=-46.66),
    )
    state = {
        "messages": [HumanMessage(content="o primeiro")],
        "trip_request": {
            "intent": "route", "origin": "Centro", "destination": "Parque",
            "mode": "DRIVE", "time_kind": "now",
        },
        "location_candidates": [{"place_id": "destination-1"}, {"place_id": "destination-2"}],
        "pending_location_role": "destination",
        "turn_agents": [],
    }
    decision = orchestrator_node.orchestrator_node(state)
    assert decision["trip_request"]["selected_place_id"] == "destination-1"
    assert decision["flow_status"] == "resolve"

    monkeypatch.setattr(location_node, "place_by_id", AsyncMock(return_value=destination))
    monkeypatch.setattr(location_node, "search_places", AsyncMock(return_value=[origin]))
    resolved = await location_node.resolve_locations_node({**state, **decision})
    assert resolved["flow_status"] == "routes"
    assert resolved["resolved_destination"]["place_id"] == "destination-1"
    assert resolved["location_candidates"] == []


def test_pending_request_is_available_to_input_guardrail(monkeypatch):
    model = Mock()
    model.invoke.return_value = AIMessage(content="CATEGORIA: APROVADO\nJUSTIFICATIVA: continuação")
    monkeypatch.setattr(input_guardrail_node, "llm_groq", Mock(return_value=model))
    result = input_guardrail_node.input_guardrail_node({
        "messages": [HumanMessage(content="o primeiro")],
        "trip_request": {"intent": "route"},
    })
    assert result["route"] == "proceed"
    assert "solicitação de deslocamento/localização pendente" in model.invoke.call_args.args[0][0].content


def test_google_results_are_not_saved_in_checkpoint():
    graph = StateGraph(GraphState)

    def add_data(_state):
        return {
            "route_options": [{"encoded_polyline": "provider-polyline"}],
            "weather_evidence": [{"condition": "provider-weather"}],
            "resolved_destination": {"address": "provider-address"},
            "route_data": {"encoded_polyline": "provider-polyline"},
            "location_candidates": [{"place_id": "allowed-place-id"}],
        }

    graph.add_node("add_data", add_data)
    graph.set_entry_point("add_data")
    workflow = graph.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "privacy-test"}}
    result = workflow.invoke({"messages": [HumanMessage(content="rota")]}, config=config)
    assert result["route_options"][0]["encoded_polyline"] == "provider-polyline"
    snapshot = workflow.get_state(config).values
    assert snapshot["location_candidates"] == [{"place_id": "allowed-place-id"}]
    for field in ("route_options", "weather_evidence", "resolved_destination", "route_data"):
        assert field not in snapshot
