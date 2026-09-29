from src.workflow.state import GraphState


def decide_post_input_guardrail(state: GraphState) -> str:
    if state["route"] == "end":
        return "end"
    return "proceed"


def decide_post_judge(state: GraphState) -> str:
    if state.get("judge_status") == "retry":
        return "retry"
    return "output_guardrail"
