from typing import Annotated

from langgraph.channels.untracked_value import UntrackedValue
from langgraph.graph import MessagesState


class GraphState(MessagesState):
    route: str
    intent: str
    flow_status: str
    trip_request: dict
    current_location: Annotated[dict | None, UntrackedValue]
    user_timezone: Annotated[str | None, UntrackedValue]
    resolved_origin: Annotated[dict, UntrackedValue]
    resolved_destination: Annotated[dict, UntrackedValue]
    origin_timezone: Annotated[str, UntrackedValue]
    destination_timezone: Annotated[str, UntrackedValue]
    route_options: Annotated[list[dict], UntrackedValue]
    weather_evidence: Annotated[list[dict], UntrackedValue]
    solar_result: Annotated[dict, UntrackedValue]
    timezone_result: Annotated[dict, UntrackedValue]
    provider_issue: str | None
    route_decision: Annotated[dict, UntrackedValue]
    route_data: Annotated[dict | None, UntrackedValue]
    output_status: str
    location_candidates: list[dict]
    pending_location_role: str | None
    turn_agents: list[str]
    summary: str
    pii_map: dict
    judge_retries: int
    judge_status: str
    user_id: str | None
    user_memory: str
