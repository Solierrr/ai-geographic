from src.workflow import config
from src.workflow.state import GraphState


def consulted_specialists(state: GraphState) -> set[str]:
    return set(state.get("turn_agents", [])) & config.SPECIALIST_ROUTES


def available_specialist_routes(state: GraphState) -> set[str]:
    return config.SPECIALIST_ROUTES - consulted_specialists(state)


def decide_post_router(state: GraphState) -> str:
    route = state.get("route", "end")
    if route == "orchestrator":
        return "orchestrator"
    if route not in config.SPECIALIST_ROUTES:
        return "end"
    if route not in available_specialist_routes(state):
        return "orchestrator"
    return route


def decide_post_input_guardrail(state: GraphState) -> str:
    if state["route"] == "end":
        return "end"
    return "proceed"


def decide_post_judge(state: GraphState) -> str:
    if state.get("judge_status") == "retry":
        return "retry"
    return "output_guardrail"
