import pytest

from src.workflow.edges.routing_edges import (
    decide_post_input_guardrail,
    decide_post_judge,
    decide_post_router,
)


def test_decide_post_input_guardrail_returns_end_for_end_route():
    assert decide_post_input_guardrail({"route": "end"}) == "end"


def test_decide_post_input_guardrail_returns_proceed_for_other_routes():
    assert decide_post_input_guardrail({"route": "example_specialist"}) == "proceed"


@pytest.mark.parametrize(
    "route",
    [
        "example_specialist",
        "example_specialist_two",
        "end",
    ],
)
def test_decide_post_router_returns_the_selected_route(route):
    assert decide_post_router({"route": route}) == route


def test_decide_post_router_returns_orchestrator_directly():
    assert decide_post_router({"route": "orchestrator"}) == "orchestrator"


def test_decide_post_router_falls_back_to_orchestrator_when_route_was_already_consulted():
    assert (
        decide_post_router(
            {
                "route": "example_specialist",
                "turn_agents": ["example_specialist", "router"],
            }
        )
        == "orchestrator"
    )


def test_decide_post_judge_returns_retry():
    assert decide_post_judge({"judge_status": "retry"}) == "retry"


def test_decide_post_judge_returns_output_guardrail_when_approved():
    assert decide_post_judge({"judge_status": "approved"}) == "output_guardrail"


def test_decide_post_judge_returns_output_guardrail_when_blocked():
    assert decide_post_judge({"judge_status": "blocked"}) == "output_guardrail"
