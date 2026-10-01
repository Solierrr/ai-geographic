import asyncio
from datetime import timedelta

from src.core.travel.models import ResolvedPlace, RouteOption
from src.core.travel.polyline import midpoint
from src.infra.external.google_geographic import hourly_weather
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


async def weather_node(state: GraphState, config=None) -> dict:
    origin = ResolvedPlace.model_validate(state["resolved_origin"])
    destination = ResolvedPlace.model_validate(state["resolved_destination"])
    routes = [RouteOption.model_validate(item) for item in state["route_options"]]
    tasks = []
    task_route_ids = []
    for route in routes:
        checks = [
            (origin.coordinate, route.departure_at, "origin"),
            (destination.coordinate, route.arrival_at, "destination"),
        ]
        middle = midpoint(route.encoded_polyline)
        if middle and route.distance_meters >= 20_000:
            checks.append(
                (
                    middle,
                    route.departure_at + timedelta(seconds=route.duration_seconds / 2),
                    "midpoint",
                )
            )
        for coordinate, at, role in checks:
            tasks.append(hourly_weather(coordinate, at, role))
            task_route_ids.append(route.route_id)
    checks = await asyncio.gather(*tasks, return_exceptions=True)
    evidence = []
    for route_id, item in zip(task_route_ids, checks):
        if item is not None and not isinstance(item, BaseException):
            evidence.append(
                item.model_copy(update={"route_id": route_id}).model_dump(mode="json")
            )
    issue = None
    if len(evidence) < len(routes) * 2:
        issue = "weather_unavailable"
    return {
        "weather_evidence": evidence,
        "provider_issue": issue,
        "flow_status": "specialist",
        "turn_agents": append_turn_agent(state, "weather"),
    }
