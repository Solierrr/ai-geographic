"""Consulta o fuso IANA de uma localização por meio do registry."""

from datetime import datetime, timezone

from langchain_core.messages import AIMessage

from src.core.travel.models import ResolvedPlace
from src.infra.external.google_registry.errors import (
    GoogleRegistryError,
    RegistryNotFoundError,
)
from src.infra.external.google_registry.geo import get_timezone
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


def _offset_text(seconds: int) -> str:
    sign = "+" if seconds >= 0 else "-"
    hours, remainder = divmod(abs(seconds), 3600)
    minutes = remainder // 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


async def timezone_node(state: GraphState, config=None) -> dict:
    result = {"turn_agents": append_turn_agent(state, "timezone")}
    language = state.get("trip_request", {}).get("response_language", "pt-BR")
    place = ResolvedPlace.model_validate(state["resolved_destination"])
    try:
        info = await get_timezone(place.coordinate, datetime.now(timezone.utc))
    except RegistryNotFoundError:
        not_found = {
            "pt-BR": "Não foi possível determinar o fuso dessa localização.",
            "en": "I could not determine the time zone for this location.",
            "es": "No fue posible determinar la zona horaria de esta ubicación.",
        }[language]
        return {
            **result,
            "flow_status": "respond",
            "provider_issue": "not_found",
            "messages": [AIMessage(content=not_found)],
        }
    except GoogleRegistryError as exc:
        unavailable = {
            "pt-BR": "A consulta de fuso está temporariamente indisponível. Tente novamente em instantes.",
            "en": "The time zone lookup is temporarily unavailable. Please try again shortly.",
            "es": "La consulta de zona horaria no está disponible temporalmente. Inténtalo de nuevo en unos instantes.",
        }[language]
        return {
            **result,
            "flow_status": "respond",
            "provider_issue": exc.kind,
            "messages": [AIMessage(content=unavailable)],
        }
    timezone_result = {
        "timezone_id": str(info.zone),
        "utc_offset_seconds": info.utc_offset_seconds,
    }
    answer = {
        "pt-BR": (
            f"O fuso IANA dessa localização é {info.zone} "
            f"({_offset_text(info.utc_offset_seconds)} neste momento)."
        ),
        "en": (
            f"The IANA time zone for this location is {info.zone} "
            f"({_offset_text(info.utc_offset_seconds)} at this time)."
        ),
        "es": (
            f"La zona horaria IANA de esta ubicación es {info.zone} "
            f"({_offset_text(info.utc_offset_seconds)} en este momento)."
        ),
    }[language]
    return {
        **result,
        "flow_status": "respond",
        "timezone_result": timezone_result,
        "messages": [
            AIMessage(content=answer)
        ],
    }
