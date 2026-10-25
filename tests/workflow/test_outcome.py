from src.workflow.outcome import (
    Outcome,
    Reason,
    record_issue,
    resolve_outcome,
    start_turn,
)


def test_answered_when_nothing_went_wrong():
    assert resolve_outcome(["router", "output_guardrail"], []) == (
        Outcome.ANSWERED,
        None,
    )


def test_refused_by_input_guardrail_category():
    assert resolve_outcome(["input_guardrail_blocked_fora_escopo"], []) == (
        Outcome.REFUSED,
        Reason.OUT_OF_SCOPE,
    )
    assert resolve_outcome(["input_guardrail_blocked_manipulacao_regex"], []) == (
        Outcome.REFUSED,
        Reason.MANIPULATION_ATTEMPT,
    )


def test_unknown_refusal_category_falls_back_to_generic_reason():
    assert resolve_outcome(["input_guardrail_blocked_outra"], []) == (
        Outcome.REFUSED,
        Reason.GUARDRAIL_REFUSED,
    )


def test_guardrail_evaluation_failure_is_degraded():
    assert resolve_outcome(
        ["input_guardrail_blocked_falha_avaliacao_guardrail"],
        [(Outcome.DEGRADED, Reason.LLM_FALLBACK)],
    ) == (Outcome.DEGRADED, Reason.GUARDRAIL_UNAVAILABLE)


def test_output_guardrail_failure_wins_over_tool_failure():
    issues = [
        (Outcome.TOOL_FAILED, Reason.MAPS_UNAVAILABLE),
        (Outcome.DEGRADED, Reason.GUARDRAIL_UNAVAILABLE),
    ]

    assert resolve_outcome(["router"], issues) == (
        Outcome.DEGRADED,
        Reason.GUARDRAIL_UNAVAILABLE,
    )


def test_tool_failure_wins_over_llm_fallback():
    issues = [
        (Outcome.DEGRADED, Reason.LLM_FALLBACK),
        (Outcome.TOOL_FAILED, Reason.SOLAR_DATA_UNAVAILABLE),
    ]

    assert resolve_outcome(["field_conditions"], issues) == (
        Outcome.TOOL_FAILED,
        Reason.SOLAR_DATA_UNAVAILABLE,
    )


def test_record_issue_fills_the_current_turn_only():
    record_issue(Outcome.TOOL_FAILED, Reason.TOOL_ERROR)
    issues = start_turn()

    record_issue(Outcome.TOOL_FAILED, Reason.MAPS_UNAVAILABLE)

    assert issues == [(Outcome.TOOL_FAILED, Reason.MAPS_UNAVAILABLE)]
