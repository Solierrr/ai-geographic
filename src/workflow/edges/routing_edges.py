from src.workflow.state import GraphState


def decide_post_input_guardrail(state: GraphState) -> str:
    if state["route"] == "end":
        return "end"
    return "proceed"


def decide_post_judge(state: GraphState) -> str:
    if state.get("judge_status") == "retry":
        return "retry"
    return "output_guardrail"


def decide_post_orchestrator(state: GraphState) -> str:
    return "resolve" if state.get("flow_status") == "resolve" else "respond"


def decide_post_location(state: GraphState) -> str:
    status = state.get("flow_status")
    return status if status in {"routes", "solar", "timezone"} else "respond"


def decide_post_routes(state: GraphState) -> str:
    return "weather" if state.get("flow_status") == "weather" else "respond"


def decide_judge_retry(state: GraphState) -> str:
    if state.get("judge_status") != "retry":
        return "end"
    return (
        "specialist"
        if state.get("intent") == "route" and state.get("route_options")
        else "orchestrator"
    )
