from src.workflow.config import SPECIALIST_ROUTES
from src.workflow.state import GraphState


def append_turn_agent(state: GraphState, agent: str) -> list[str]:
    return [*state.get("turn_agents", []), agent]


def specialists_used(turn_agents: list[str]) -> list[str]:
    return [agent for agent in turn_agents if agent in SPECIALIST_ROUTES]
