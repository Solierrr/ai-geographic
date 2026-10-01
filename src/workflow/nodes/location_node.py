from langchain_core.messages import AIMessage

from src.core.travel.models import Coordinate, ResolvedPlace
from src.infra.external.google_geographic import (
    GeographicProviderError,
    place_by_id,
    search_places,
)
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


def _question_for_candidates(label: str, places: list[ResolvedPlace]) -> str:
    choices = "; ".join(f"{place.label} — {place.address}" for place in places[:3])
    return f"Encontrei mais de um lugar para {label}: {choices}. Qual deles você quer dizer?"


async def resolve_locations_node(state: GraphState, config=None) -> dict:
    request = state["trip_request"]
    result: dict = {"turn_agents": append_turn_agent(state, "location")}
    selected_id = request.get("selected_place_id")
    selected_role = state.get("pending_location_role")
    try:
        selected = (
            await place_by_id(selected_id) if selected_id and selected_role else None
        )
        if request["intent"] == "route":
            origin_text = (request.get("origin") or "").strip()
            current = state.get("current_location")
            if (
                not origin_text
                or origin_text.casefold() in {"aqui", "minha localização", "onde estou"}
            ) and current:
                origin = ResolvedPlace(
                    label="Sua localização informada",
                    address="Localização fornecida neste pedido",
                    coordinate=Coordinate.model_validate(current),
                )
            elif not origin_text or origin_text.casefold() in {
                "aqui",
                "minha localização",
                "onde estou",
            }:
                return {
                    **result,
                    "flow_status": "respond",
                    "messages": [AIMessage(content="De onde você vai sair?")],
                }
            else:
                origins = (
                    [selected]
                    if selected and selected_role == "origin"
                    else await search_places(origin_text)
                )
                if not origins:
                    return {
                        **result,
                        "flow_status": "respond",
                        "messages": [
                            AIMessage(
                                content=f"Não encontrei a origem “{origin_text}”. Pode informar um endereço ou lugar mais específico?"
                            )
                        ],
                    }
                if len(origins) > 1:
                    return {
                        **result,
                        "flow_status": "respond",
                        "location_candidates": [
                            {"place_id": item.place_id} for item in origins
                        ],
                        "pending_location_role": "origin",
                        "messages": [
                            AIMessage(
                                content=_question_for_candidates("a origem", origins)
                            )
                        ],
                    }
                origin = origins[0]
            result["resolved_origin"] = origin.model_dump(mode="json")

        destinations = (
            [selected]
            if selected and selected_role == "destination"
            else await search_places(request["destination"])
        )
        if not destinations:
            return {
                **result,
                "flow_status": "respond",
                "messages": [
                    AIMessage(
                        content=f"Não encontrei “{request['destination']}”. Pode informar um endereço ou lugar mais específico?"
                    )
                ],
            }
        if len(destinations) > 1:
            return {
                **result,
                "flow_status": "respond",
                "location_candidates": [
                    {"place_id": item.place_id} for item in destinations
                ],
                "pending_location_role": "destination",
                "messages": [
                    AIMessage(
                        content=_question_for_candidates("o destino", destinations)
                    )
                ],
            }
        destination = destinations[0]
        result["resolved_destination"] = destination.model_dump(mode="json")
        result["location_candidates"] = []
        result["pending_location_role"] = None
        if request["intent"] == "locate":
            result["flow_status"] = "respond"
            result["messages"] = [
                AIMessage(
                    content=f"{destination.label} fica em {destination.address}. Dados de localização: Google Maps."
                )
            ]
        else:
            result["flow_status"] = "routes"
        return result
    except GeographicProviderError as exc:
        return {
            **result,
            "flow_status": "respond",
            "provider_issue": exc.kind,
            "messages": [
                AIMessage(
                    content="Não consegui consultar a localização agora. Tente novamente em instantes."
                )
            ],
        }
