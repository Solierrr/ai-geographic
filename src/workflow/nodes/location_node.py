from langchain_core.messages import AIMessage

from src.core.travel.models import Coordinate, ResolvedPlace
from src.infra.external.google_registry.address import (
    place_by_id,
    search_places,
)
from src.infra.external.google_registry.errors import (
    GoogleRegistryError,
    RegistryNotFoundError,
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
    language = request.get("response_language", "pt-BR")
    registry_language = {"pt-BR": "pt-BR", "en": "en", "es": "es"}[language]
    try:
        selected = (
            await place_by_id(selected_id, language=registry_language)
            if selected_id and selected_role
            else None
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
                    else await search_places(origin_text, language=registry_language)
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
                    if any(item.place_id is None for item in origins):
                        return {
                            **result,
                            "flow_status": "respond",
                            "messages": [
                                AIMessage(
                                    content="Encontrei mais de uma origem possível. Informe um endereço mais específico."
                                )
                            ],
                        }
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

        destination_text = (request.get("destination") or "").strip()
        current = state.get("current_location")
        current_aliases = {
            "aqui",
            "minha localização",
            "onde estou",
            "here",
            "my location",
            "aquí",
            "mi ubicación",
        }
        if request["intent"] != "route" and (
            not destination_text or destination_text.casefold() in current_aliases
        ):
            if current:
                destinations = [
                    ResolvedPlace(
                        label="Localização atual",
                        address="Localização fornecida neste pedido",
                        coordinate=Coordinate.model_validate(current),
                    )
                ]
            else:
                question = {
                    "solar": {
                        "pt-BR": "Qual é o endereço para a análise solar?",
                        "en": "What address should I use for the solar analysis?",
                        "es": "¿Qué dirección debo usar para el análisis solar?",
                    },
                    "timezone": {
                        "pt-BR": "De qual endereço ou localização você quer saber o fuso?",
                        "en": "Which address or location do you want the time zone for?",
                        "es": "¿De qué dirección o ubicación quieres saber la zona horaria?",
                    },
                    "locate": {
                        "pt-BR": "Qual endereço ou lugar você quer localizar?",
                        "en": "Which address or place do you want to locate?",
                        "es": "¿Qué dirección o lugar quieres localizar?",
                    },
                }[request["intent"]][language]
                return {
                    **result,
                    "flow_status": "respond",
                    "messages": [AIMessage(content=question)],
                }
        else:
            destinations = (
                [selected]
                if selected and selected_role == "destination"
                else await search_places(destination_text, language=registry_language)
            )
        if not destinations:
            return {
                **result,
                "flow_status": "respond",
                "messages": [
                    AIMessage(
                        content=f"Não encontrei “{destination_text}”. Pode informar um endereço ou lugar mais específico?"
                    )
                ],
            }
        if len(destinations) > 1:
            if any(item.place_id is None for item in destinations):
                return {
                    **result,
                    "flow_status": "respond",
                    "messages": [
                        AIMessage(
                            content="Encontrei mais de uma localização possível. Informe um endereço mais específico."
                        )
                    ],
                }
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
            result["flow_status"] = (
                "routes" if request["intent"] == "route" else request["intent"]
            )
        return result
    except RegistryNotFoundError as exc:
        return {
            **result,
            "flow_status": "respond",
            "provider_issue": exc.kind,
            "messages": [
                AIMessage(
                    content=(
                        "Não encontrei esse endereço ou lugar. "
                        "Pode informar uma localização mais específica?"
                    )
                )
            ],
        }
    except GoogleRegistryError as exc:
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
