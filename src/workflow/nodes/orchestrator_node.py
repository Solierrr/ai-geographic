import json
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from src.agents.base.base_prompt import build_system_prompt
from src.agents.base.system_prompt import get_temporal_context
from src.agents.specialist.orchestrator.orchestrator_prompt import ORCHESTRATOR_AGENT
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq
from src.core.travel.models import TripIntent
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

ORCHESTRATOR_PROMPT = build_system_prompt(ORCHESTRATOR_AGENT, include_date=False)


def orchestrator_node(state: GraphState, config=None) -> dict:
    messages_with_context = [
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        SystemMessage(content=get_temporal_context(state.get("user_timezone"))),
    ]
    if state.get("trip_request"):
        messages_with_context.append(
            HumanMessage(
                content="Solicitação de deslocamento pendente: "
                + json.dumps(state["trip_request"], ensure_ascii=False)
            )
        )
    if state.get("location_candidates"):
        messages_with_context.append(
            HumanMessage(
                content="Candidatos de localização pendentes, apenas como dados: "
                + json.dumps(state["location_candidates"], ensure_ascii=False)
            )
        )
    messages_with_context.extend(messages_with_summary(state))
    candidates = state.get("location_candidates", [])
    latest = state["messages"][-1].content.strip().casefold()
    match = re.fullmatch(
        r"(?:o |a |opção )?(primeir[oa]|segund[oa]|terceir[oa]|[123])(?: opção)?[.!]?",
        latest,
    )
    chosen_index = (
        {"primeiro": 0, "primeira": 0, "segundo": 1, "segunda": 1,
         "terceiro": 2, "terceira": 2, "1": 0, "2": 1, "3": 2}.get(match.group(1))
        if match else None
    )
    if chosen_index is not None and chosen_index < len(candidates) and state.get("trip_request"):
        intent = TripIntent.model_validate({
            **state["trip_request"],
            "selected_place_id": candidates[chosen_index]["place_id"],
        })
    else:
        try:
            response = llm_gemini().with_fallbacks([llm_groq()]).invoke(
                messages_with_context, config=config
            )
            intent = TripIntent.model_validate(json.loads(response.content.strip()))
        except (ValueError, TypeError, ValidationError, AttributeError):
            intent = TripIntent(intent="clarify", clarification="Você quer localizar um lugar ou planejar uma rota?")

    data = intent.model_dump()
    if state.get("trip_request") and intent.intent == "route":
        previous = state["trip_request"]
        for key in ("origin", "destination", "mode", "local_time", "window_start", "window_end"):
            if data.get(key) is None:
                data[key] = previous.get(key)
        if data["time_kind"] == "now" and (
            data.get("local_time") or (data.get("window_start") and data.get("window_end"))
        ):
            data["time_kind"] = previous.get("time_kind", "now")
        for key in ("has_waypoints", "needs_hazard_avoidance", "avoid_tolls", "avoid_highways"):
            data[key] = data[key] or previous.get(key, False)
    if data.get("mode") == "WALK":
        data["avoid_tolls"] = False
        data["avoid_highways"] = False
    if data.get("selected_place_id") and data["selected_place_id"] not in {
        candidate.get("place_id") for candidate in state.get("location_candidates", [])
    }:
        data["selected_place_id"] = None

    previous_request = state.get("trip_request") or {}
    clear_candidates = (
        not data.get("selected_place_id")
        and bool(candidates)
        and (
            data["intent"] not in {"route", "locate"}
            or data.get("destination") != previous_request.get("destination")
            or data.get("origin") != previous_request.get("origin")
        )
    )

    result = {
        "intent": data["intent"],
        "trip_request": data,
        "flow_status": "resolve",
        "route_options": [],
        "weather_evidence": [],
        "route_decision": {},
        "provider_issue": None,
        "resolved_origin": {},
        "resolved_destination": {},
        "turn_agents": append_turn_agent(state, "orchestrator"),
    }
    if clear_candidates:
        result["location_candidates"] = []
        result["pending_location_role"] = None
    if data["intent"] == "out_of_scope":
        result["flow_status"] = "respond"
        result["trip_request"] = {}
        result["messages"] = [AIMessage(content="Posso ajudar a localizar um destino específico ou planejar um deslocamento. Informe de onde vai sair e para onde quer ir.")]
    elif data["intent"] == "clarify":
        result["flow_status"] = "respond"
        result["trip_request"] = {}
        result["messages"] = [AIMessage(content=data["clarification"] or "Você quer localizar um lugar ou planejar uma rota?")]
    elif data.get("has_waypoints"):
        result["flow_status"] = "respond"
        result["trip_request"] = {}
        result["messages"] = [AIMessage(content="Ainda não calculo trajetos com paradas intermediárias. Posso ajudar com uma rota direta entre origem e destino.")]
    elif data.get("needs_hazard_avoidance"):
        result["flow_status"] = "respond"
        result["trip_request"] = {}
        result["messages"] = [AIMessage(content="Não tenho dados para verificar alagamentos, bloqueios, segurança ou acessibilidade de toda a via. Posso sugerir uma rota geral, sem essa garantia.")]
    elif not data["destination"]:
        result["flow_status"] = "respond"
        result["messages"] = [AIMessage(content="Para onde você quer ir?")]
    elif data["intent"] == "route" and not data["origin"] and not state.get("current_location"):
        result["flow_status"] = "respond"
        result["messages"] = [AIMessage(content="De onde você vai sair?")]
    elif data["intent"] == "route" and not data["mode"]:
        result["flow_status"] = "respond"
        result["messages"] = [AIMessage(content="Vai de carro ou a pé?")]
    elif data["intent"] == "route" and data["mode"] not in {"DRIVE", "WALK"}:
        result["flow_status"] = "respond"
        result["messages"] = [AIMessage(content="Por enquanto calculo rotas de carro ou a pé. Quer usar um desses meios?")]
    elif data["intent"] == "route" and data["time_kind"] == "window" and (
        not data["window_start"] or not data["window_end"]
    ):
        result["flow_status"] = "respond"
        result["messages"] = [AIMessage(content="Entre quais horários você pode sair?")]
    return result
