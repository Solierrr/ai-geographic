from src.workflow.state import GraphState


def append_turn_agent(state: GraphState, agent: str) -> list[str]:
    return [*state.get("turn_agents", []), agent]
