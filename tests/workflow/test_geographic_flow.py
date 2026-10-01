from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from src.core.travel.models import (
    Coordinate,
    ResolvedPlace,
    RouteOption,
    WeatherEvidence,
)
from src.workflow.nodes import (
    input_guardrail_node,
    judge_node,
    location_node,
    orchestrator_node,
    output_guardrail_node,
    route_specialist_node,
    routes_node,
    weather_node,
)


def _place(name: str, latitude: float = -23.5) -> ResolvedPlace:
    return ResolvedPlace(
        label=name,
        address=f"{name}, São Paulo - SP",
        coordinate=Coordinate(latitude=latitude, longitude=-46.6),
        place_id=f"id-{name}",
    )


def _route(route_id: str, minutes: int, departure: datetime) -> RouteOption:
    return RouteOption(
        route_id=route_id,
        duration_seconds=minutes * 60,
        distance_meters=8000,
        departure_at=departure,
        arrival_at=departure + timedelta(minutes=minutes),
    )


def test_nonexistent_dst_time_is_rejected():
    with pytest.raises(ValueError):
        routes_node._local_to_utc(
            datetime(2026, 3, 8, 2, 30),  # noqa: DTZ001 - horário local recebido sem fuso
            ZoneInfo("America/New_York"),
        )


@pytest.mark.asyncio
async def test_location_asks_when_google_returns_ambiguous_destination(monkeypatch):
    monkeypatch.setattr(
        location_node,
        "search_places",
        AsyncMock(return_value=[_place("Santa Cruz SP"), _place("Santa Cruz RJ")]),
    )
    state = {
        "trip_request": {"intent": "locate", "destination": "Santa Cruz"},
        "turn_agents": [],
    }
    result = await location_node.resolve_locations_node(state)
    assert result["flow_status"] == "respond"
    assert "Qual deles" in result["messages"][0].content


@pytest.mark.asyncio
async def test_routes_window_creates_three_real_departure_slots(monkeypatch):
    base = datetime.now(timezone.utc) + timedelta(days=1)
    local = base.astimezone(ZoneInfo("America/Sao_Paulo"))
    start = local.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=2)
    monkeypatch.setattr(
        routes_node, "timezone_for", AsyncMock(return_value=ZoneInfo("America/Sao_Paulo"))
    )

    async def fake_compute(_origin, _destination, _mode, departure):
        return [_route("route-1", 25, departure), _route("route-2", 40, departure)]

    monkeypatch.setattr(routes_node, "compute_routes", fake_compute)
    state = {
        "trip_request": {
            "intent": "route",
            "mode": "DRIVE",
            "time_kind": "window",
            "window_start": start.strftime("%Y-%m-%dT%H:%M"),
            "window_end": end.strftime("%Y-%m-%dT%H:%M"),
        },
        "resolved_origin": _place("Origem").model_dump(mode="json"),
        "resolved_destination": _place("Destino").model_dump(mode="json"),
        "turn_agents": [],
    }
    result = await routes_node.routes_node(state)
    assert result["flow_status"] == "weather"
    assert [item["route_id"] for item in result["route_options"]] == [
        "slot-1", "slot-2", "slot-3"
    ]


@pytest.mark.asyncio
async def test_weather_failure_keeps_route_and_marks_limitation(monkeypatch):
    departure = datetime.now(timezone.utc) + timedelta(hours=1)
    monkeypatch.setattr(
        weather_node,
        "hourly_weather",
        AsyncMock(side_effect=RuntimeError("provider down")),
    )
    state = {
        "resolved_origin": _place("Origem").model_dump(mode="json"),
        "resolved_destination": _place("Destino").model_dump(mode="json"),
        "route_options": [_route("route-1", 20, departure).model_dump(mode="json")],
        "turn_agents": [],
    }
    result = await weather_node.weather_node(state)
    assert result["flow_status"] == "specialist"
    assert result["weather_evidence"] == []
    assert result["provider_issue"] == "weather_unavailable"


def test_specialist_chooses_drier_slot_when_evidence_supports_it(monkeypatch):
    departure = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)
    routes = [_route("slot-1", 20, departure), _route("slot-2", 24, departure + timedelta(hours=1))]
    evidence = []
    for route, rain in [(routes[0], 80), (routes[1], 20)]:
        for role, at in [("origin", route.departure_at), ("destination", route.arrival_at)]:
            evidence.append(
                WeatherEvidence(
                    role=role,
                    route_id=route.route_id,
                    at=at,
                    interval_start=at,
                    interval_end=at + timedelta(hours=1),
                    precipitation_probability=rain,
                    fetched_at=departure,
                ).model_dump(mode="json")
            )
    model = Mock()
    model.invoke.return_value = SimpleNamespace(content="invalid")
    gemini = Mock()
    gemini.with_fallbacks.return_value = model
    monkeypatch.setattr(route_specialist_node, "llm_gemini", Mock(return_value=gemini))
    monkeypatch.setattr(route_specialist_node, "llm_groq", Mock())
    state = {
        "trip_request": {"mode": "DRIVE", "time_kind": "window"},
        "resolved_origin": _place("Origem").model_dump(mode="json"),
        "resolved_destination": _place("Destino").model_dump(mode="json"),
        "origin_timezone": "America/Sao_Paulo",
        "destination_timezone": "America/Sao_Paulo",
        "route_options": [route.model_dump(mode="json") for route in routes],
        "weather_evidence": evidence,
        "turn_agents": [],
    }
    result = route_specialist_node.route_specialist_node(state)
    assert result["route_decision"]["route_id"] == "slot-2"
    assert result["route_decision"]["rationale"] == "weather"
    assert "80%" in result["messages"][0].content


@pytest.mark.asyncio
async def test_graph_recommends_route_and_returns_only_ephemeral_provider_data(monkeypatch):
    from src.workflow.graph.graph import graph

    approved = Mock()
    approved.invoke.return_value = AIMessage(content="CATEGORIA: APROVADO\nJUSTIFICATIVA: rota")
    monkeypatch.setattr(input_guardrail_node, "llm_groq", Mock(return_value=approved))

    intent_model = Mock()
    intent_model.invoke.return_value = AIMessage(content=(
        '{"intent":"route","origin":"Centro","destination":"Parque",'
        '"mode":"DRIVE","time_kind":"now"}'
    ))
    gemini = Mock()
    gemini.with_fallbacks.return_value = intent_model
    monkeypatch.setattr(orchestrator_node, "llm_gemini", Mock(return_value=gemini))
    monkeypatch.setattr(orchestrator_node, "llm_groq", Mock())

    monkeypatch.setattr(location_node, "search_places", AsyncMock(side_effect=[
        [_place("Centro")], [_place("Parque", latitude=-23.6)],
    ]))
    monkeypatch.setattr(routes_node, "timezone_for", AsyncMock(return_value=ZoneInfo("America/Sao_Paulo")))

    async def fake_routes(_origin, _destination, _mode, departure):
        return [_route("route-1", 25, departure).model_copy(update={"encoded_polyline": "provider-polyline"})]

    monkeypatch.setattr(routes_node, "compute_routes", fake_routes)
    monkeypatch.setattr(weather_node, "hourly_weather", AsyncMock(return_value=None))
    specialist_model = Mock()
    specialist_model.invoke.return_value = AIMessage(content="invalid")
    specialist_gemini = Mock()
    specialist_gemini.with_fallbacks.return_value = specialist_model
    monkeypatch.setattr(route_specialist_node, "llm_gemini", Mock(return_value=specialist_gemini))
    monkeypatch.setattr(route_specialist_node, "llm_groq", Mock())

    reviewed_texts = []

    def output_review(messages, config=None):
        reviewed = messages[0].content.split("Resposta para revisar:\n\n", 1)[1].split(
            "Responda EXATAMENTE", 1
        )[0].strip()
        reviewed_texts.append(reviewed)
        return AIMessage(content=f"STATUS: APROVADO\nRESPOSTA: {reviewed}")

    review_model = Mock()
    review_model.invoke.side_effect = output_review
    monkeypatch.setattr(output_guardrail_node, "llm_groq", Mock(return_value=review_model))
    judge_model = Mock()
    judge_model.invoke.return_value = AIMessage(content="STATUS: APROVADO\nJUSTIFICATIVA: dados conferidos")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=judge_model))

    workflow = graph.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "graph-route-test"}}
    final = await workflow.ainvoke({
        "messages": [HumanMessage(content="Como vou do Centro ao Parque de carro agora?")],
        "turn_agents": [], "judge_retries": 0,
    }, config=config)
    assert final["judge_status"] == "approved"
    assert final["route_data"] is not None, (final["turn_agents"], reviewed_texts)
    assert final["route_data"]["encoded_polyline"] == "provider-polyline"
    assert "25 min" in final["messages"][-1].content
    stored = (await workflow.aget_state(config)).values
    assert "route_options" not in stored
    assert "weather_evidence" not in stored
    assert "route_data" not in stored

