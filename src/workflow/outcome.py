"""Resultado do turno (`outcome` e `reason`) para o front mostrar a mensagem certa.

O que acontece dentro da conversa não é erro HTTP: guardrail que recusa, ferramenta
que falha e provedor que cai voltam 200, com o resultado nestes dois campos."""

from contextvars import ContextVar
from enum import StrEnum


class Outcome(StrEnum):
    ANSWERED = "ANSWERED"
    REFUSED = "REFUSED"
    DEGRADED = "DEGRADED"
    TOOL_FAILED = "TOOL_FAILED"


class Reason(StrEnum):
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    MANIPULATION_ATTEMPT = "MANIPULATION_ATTEMPT"
    INTERNAL_DATA_REQUEST = "INTERNAL_DATA_REQUEST"
    FALSE_INFORMATION = "FALSE_INFORMATION"
    GUARDRAIL_REFUSED = "GUARDRAIL_REFUSED"
    GUARDRAIL_UNAVAILABLE = "GUARDRAIL_UNAVAILABLE"
    LLM_FALLBACK = "LLM_FALLBACK"
    MAPS_UNAVAILABLE = "MAPS_UNAVAILABLE"
    SOLAR_DATA_UNAVAILABLE = "SOLAR_DATA_UNAVAILABLE"
    PRODUCT_ADVISOR_UNAVAILABLE = "PRODUCT_ADVISOR_UNAVAILABLE"
    TOOL_ERROR = "TOOL_ERROR"


_BLOCKED_PREFIX = "input_guardrail_blocked_"

_REFUSAL_REASONS = {
    "fora_escopo": Reason.OUT_OF_SCOPE,
    "redirecionar": Reason.OUT_OF_SCOPE,
    "manipulacao": Reason.MANIPULATION_ATTEMPT,
    "manipulacao_regex": Reason.MANIPULATION_ATTEMPT,
    "dados_internos": Reason.INTERNAL_DATA_REQUEST,
    "dados_internos_regex": Reason.INTERNAL_DATA_REQUEST,
    "informacao_falsa": Reason.FALSE_INFORMATION,
}

_PRECEDENCE = (Outcome.REFUSED, Outcome.TOOL_FAILED, Outcome.DEGRADED)

_turn_issues: ContextVar[list[tuple[Outcome, Reason]] | None] = ContextVar(
    "turn_issues", default=None
)


def start_turn() -> list[tuple[Outcome, Reason]]:
    issues: list[tuple[Outcome, Reason]] = []
    _turn_issues.set(issues)
    return issues


def record_issue(outcome: Outcome, reason: Reason) -> None:
    issues = _turn_issues.get()
    if issues is not None:
        issues.append((outcome, reason))


def resolve_outcome(
    turn_agents: list[str], issues: list[tuple[Outcome, Reason]]
) -> tuple[Outcome, Reason | None]:
    for agent in turn_agents:
        if agent.startswith(_BLOCKED_PREFIX):
            category = agent.removeprefix(_BLOCKED_PREFIX)
            if category == "falha_avaliacao_guardrail":
                return Outcome.DEGRADED, Reason.GUARDRAIL_UNAVAILABLE
            return Outcome.REFUSED, _REFUSAL_REASONS.get(
                category, Reason.GUARDRAIL_REFUSED
            )

    if (Outcome.DEGRADED, Reason.GUARDRAIL_UNAVAILABLE) in issues:
        return Outcome.DEGRADED, Reason.GUARDRAIL_UNAVAILABLE

    for outcome in _PRECEDENCE:
        for issue_outcome, reason in issues:
            if issue_outcome == outcome:
                return outcome, reason
    return Outcome.ANSWERED, None
