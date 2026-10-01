import json
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.route.route_prompt import ROUTE_AGENT
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq
from src.core.travel.models import RouteDecision, RouteOption, WeatherEvidence
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


def _duration_text(seconds: int) -> str:
    minutes = round(seconds / 60)
    hours, remainder = divmod(minutes, 60)
    return f"{hours} h {remainder} min" if hours else f"{remainder} min"


def _format_time(value: datetime, zone: str) -> str:
    local = value.astimezone(ZoneInfo(zone))
    return local.strftime("%d/%m/%Y às %H:%M")


def route_specialist_node(state: GraphState, config=None) -> dict:
    routes = [RouteOption.model_validate(item) for item in state["route_options"]]
    fastest = min(routes, key=lambda route: route.duration_seconds)
    evidence = [
        WeatherEvidence.model_validate(item)
        for item in state.get("weather_evidence", [])
    ]
    rain_risk: dict[str, int] = {}
    for route in routes:
        values = [
            item.precipitation_probability
            for item in evidence
            if item.route_id == route.route_id
            and item.precipitation_probability is not None
        ]
        if len(values) >= 2:
            rain_risk[route.route_id] = max(values)
    recommended = fastest
    reason = "shortest_time"
    if len(rain_risk) == len(routes) and len(routes) > 1:
        allowed_delay = max(1200, round(fastest.duration_seconds * 0.25))
        candidates = [
            route
            for route in routes
            if route.duration_seconds <= fastest.duration_seconds + allowed_delay
        ]
        drier = min(
            candidates,
            key=lambda route: (rain_risk[route.route_id], route.duration_seconds),
        )
        if rain_risk[fastest.route_id] - rain_risk[drier.route_id] >= 20:
            recommended = drier
            reason = "weather"
    prompt = [
        SystemMessage(content=build_system_prompt(ROUTE_AGENT)),
        HumanMessage(
            content=json.dumps(
                {
                    "request": state["trip_request"],
                    "routes": [
                        route.model_dump(mode="json", exclude={"encoded_polyline"})
                        for route in routes
                    ],
                    "weather": state.get("weather_evidence", []),
                    "recommended_route_id": recommended.route_id,
                    "recommended_reason": reason,
                },
                ensure_ascii=False,
            )
        ),
    ]
    try:
        response = (
            llm_gemini().with_fallbacks([llm_groq()]).invoke(prompt, config=config)
        )
        choice = RouteDecision.model_validate(json.loads(response.content.strip()))
        if choice.route_id != recommended.route_id or choice.rationale != reason:
            raise ValueError("Escolha sem evidência")
        selected = next(route for route in routes if route.route_id == choice.route_id)
    except (ValueError, TypeError, AttributeError):
        selected = recommended
        choice = RouteDecision(
            route_id=selected.route_id,
            rationale=reason,
            weather_used=reason == "weather",
        )

    origin_zone = state["origin_timezone"]
    destination_zone = state["destination_timezone"]
    mode = state["trip_request"]["mode"]
    mode_label = "de carro" if mode == "DRIVE" else "a pé"
    line = (
        f"Sugiro a rota {selected.route_id} {mode_label} de "
        f"{state['resolved_origin']['label']} até {state['resolved_destination']['label']}. "
        f"Distância estimada: {selected.distance_meters / 1000:.1f} km; "
        f"duração estimada: {_duration_text(selected.duration_seconds)}. "
        f"Saída estimada: {_format_time(selected.departure_at, origin_zone)}; "
        f"chegada estimada: {_format_time(selected.arrival_at, destination_zone)}."
    )
    line += f" Rota consultada em {_format_time(selected.fetched_at, origin_zone)}."
    if choice.rationale == "shortest_time":
        line += " Escolhi a menor duração entre as rotas retornadas."
    elif choice.rationale == "weather":
        line += (
            f" Entre os pontos e horários consultados, a maior chance de precipitação "
            f"nessa opção foi {rain_risk[selected.route_id]}%, frente a "
            f"{rain_risk[fastest.route_id]}% na opção mais rápida."
        )
    requested_filters = []
    if state["trip_request"].get("avoid_tolls"):
        requested_filters.append("pedágios")
    if state["trip_request"].get("avoid_highways"):
        requested_filters.append("rodovias")
    if requested_filters:
        line += (
            " Solicitei ao Google Maps preferência por evitar "
            + " e ".join(requested_filters)
            + "; isso não garante ausência total."
        )
    selected_evidence = [
        item for item in evidence if item.route_id == selected.route_id
    ]
    if selected_evidence:
        details = []
        for item in selected_evidence:
            where = {
                "origin": "na origem",
                "destination": "no destino",
                "midpoint": "no ponto intermediário",
            }[item.role]
            if item.precipitation_probability is not None:
                details.append(
                    f"{item.precipitation_probability}% de chance de precipitação {where}"
                )
        if details:
            line += (
                " Previsão para os horários consultados: " + "; ".join(details) + "."
            )
        line += " A previsão não confirma as condições de cada trecho da via. Source: Includes weather data from Google."
    else:
        line += " Não consegui obter previsão para esse período; a escolha considera apenas as rotas disponíveis."
    if mode == "WALK":
        line += " Aviso: rotas a pé estão em beta e podem não incluir calçadas ou caminhos de pedestres adequados."
    line += " Dados de rota: Google Maps. Os tempos podem mudar."
    return {
        "messages": [AIMessage(content=line)],
        "route_decision": choice.model_dump(),
        "turn_agents": append_turn_agent(state, "route_specialist"),
    }
