from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage

from src.core.travel.models import ResolvedPlace
from src.infra.external.google_geographic import (
    GeographicProviderError,
    compute_routes,
    timezone_for,
)
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


def _local_to_utc(value: datetime, zone: ZoneInfo) -> datetime:
    if value.tzinfo is not None:
        raise ValueError("Horário deve ser local")
    first = value.replace(tzinfo=zone, fold=0)
    second = value.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset():
        raise ValueError("Horário local ambíguo ou inexistente")
    utc_value = first.astimezone(timezone.utc)
    if utc_value.astimezone(zone).replace(tzinfo=None) != value:
        raise ValueError("Horário local inexistente")
    return utc_value


async def routes_node(state: GraphState, config=None) -> dict:
    request = state["trip_request"]
    origin = ResolvedPlace.model_validate(state["resolved_origin"])
    destination = ResolvedPlace.model_validate(state["resolved_destination"])
    result: dict = {"turn_agents": append_turn_agent(state, "routes")}
    modifiers = {
        key: True for key, enabled in (
            ("avoidTolls", request.get("avoid_tolls")),
            ("avoidHighways", request.get("avoid_highways")),
        ) if enabled
    }

    async def calculate(departure: datetime):
        if modifiers:
            return await compute_routes(
                origin.coordinate, destination.coordinate, request["mode"],
                departure, modifiers=modifiers,
            )
        return await compute_routes(
            origin.coordinate, destination.coordinate, request["mode"], departure
        )

    try:
        now = datetime.now(timezone.utc)
        origin_zone = await timezone_for(origin.coordinate, now)
        destination_zone = await timezone_for(destination.coordinate, now)
        result["origin_timezone"] = str(origin_zone)
        result["destination_timezone"] = str(destination_zone)
        if request["time_kind"] == "window":
            start_local = datetime.fromisoformat(request["window_start"])
            end_local = datetime.fromisoformat(request["window_end"])
            if start_local.tzinfo or end_local.tzinfo or end_local <= start_local:
                raise ValueError("Janela inválida")
            if end_local - start_local > timedelta(hours=8):
                return {**result, "flow_status": "respond", "messages": [AIMessage(content="Para comparar horários, informe uma janela de até oito horas.")]}
            start = _local_to_utc(start_local, origin_zone)
            end = _local_to_utc(end_local, origin_zone)
            if start < now + timedelta(minutes=1):
                return {**result, "flow_status": "respond", "messages": [AIMessage(content="Essa janela já começou ou passou. Informe uma janela futura.")]}
            departures = [start, start + (end - start) / 2, end]
            options = []
            for index, slot in enumerate(departures, start=1):
                candidates = await calculate(slot)
                if candidates:
                    best = min(candidates, key=lambda item: item.duration_seconds)
                    options.append(best.model_copy(update={"route_id": f"slot-{index}"}))
            if not options:
                return {**result, "flow_status": "respond", "messages": [AIMessage(content="Não encontrei rotas para os horários dessa janela.")]}
            result["route_options"] = [item.model_dump(mode="json") for item in options]
            result["flow_status"] = "weather"
            return result
        if request["time_kind"] == "now":
            departure = now + timedelta(minutes=1)
        else:
            naive = datetime.fromisoformat(request["local_time"])
            target_zone = destination_zone if request["time_kind"] == "arrival" else origin_zone
            target = _local_to_utc(naive, target_zone)
            if request["time_kind"] == "arrival" and target <= now:
                return {**result, "flow_status": "respond", "messages": [AIMessage(content="Esse horário de chegada já passou. Qual data e horário futuros você quer consultar?")]}
            departure = target if request["time_kind"] == "departure" else max(now + timedelta(minutes=1), target - timedelta(hours=1))
        if request["time_kind"] != "arrival" and departure < now - timedelta(minutes=2):
            return {**result, "flow_status": "respond", "messages": [AIMessage(content="A data informada já passou. Qual data e horário futuros você quer consultar?")]}
        departure = max(departure, datetime.now(timezone.utc) + timedelta(minutes=1))
        routes = await calculate(departure)
        if not routes:
            return {**result, "flow_status": "respond", "messages": [AIMessage(content="Não encontrei uma rota para esses lugares e esse meio de transporte. Pode conferir a origem e o destino?")]}
        if request["time_kind"] == "arrival":
            departure = target - timedelta(seconds=min(route.duration_seconds for route in routes))
            if departure < datetime.now(timezone.utc) + timedelta(minutes=1):
                return {**result, "flow_status": "respond", "messages": [AIMessage(content="Com as estimativas atuais, não há tempo suficiente para chegar nesse horário. Quer tentar outro horário?")]}
            routes = await calculate(departure)
            routes = [route for route in routes if route.arrival_at <= target]
            if not routes:
                return {**result, "flow_status": "respond", "messages": [AIMessage(content="Não encontrei uma rota para esse horário de chegada. Quer tentar outro horário?")]}
        result["route_options"] = [route.model_dump(mode="json") for route in routes]
        result["flow_status"] = "weather"
        return result
    except (ValueError, KeyError, TypeError):
        return {**result, "flow_status": "respond", "messages": [AIMessage(content="Não consegui interpretar o horário. Informe a data e a hora desejadas, por exemplo: amanhã às 15h.")]}
    except GeographicProviderError as exc:
        return {**result, "flow_status": "respond", "provider_issue": exc.kind, "messages": [AIMessage(content="Não consegui calcular a rota agora. Tente novamente em instantes.")]}
