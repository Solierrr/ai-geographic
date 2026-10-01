from src.workflow.edges.routing_edges import (
    decide_post_input_guardrail,
    decide_post_judge,
)


def test_decide_post_input_guardrail_returns_end_for_end_route():
    assert decide_post_input_guardrail({"route": "end"}) == "end"


def test_decide_post_input_guardrail_returns_proceed_for_other_routes():
    assert decide_post_input_guardrail({"route": "proceed"}) == "proceed"


def test_decide_post_judge_returns_retry():
    assert decide_post_judge({"judge_status": "retry"}) == "retry"


def test_decide_post_judge_returns_output_guardrail_when_approved():
    assert decide_post_judge({"judge_status": "approved"}) == "output_guardrail"


def test_decide_post_judge_returns_output_guardrail_when_blocked():
    assert decide_post_judge({"judge_status": "blocked"}) == "output_guardrail"
