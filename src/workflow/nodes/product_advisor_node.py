import logging

from ai_lib.a2a import DelegationError, delegate
from langchain_core.messages import AIMessage, HumanMessage

from src.core.config.settings import settings
from src.core.security.request_context import current_user_token
from src.workflow.outcome import Outcome, Reason, record_issue
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

logger = logging.getLogger(__name__)

_INDISPONIVEL = "Não consegui falar com o assistente de produtos agora. Tente novamente em instantes."
_SEM_TOKEN = "Para consultar produtos é preciso estar autenticado."


def _last_user_text(state: GraphState) -> str:
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


async def product_advisor_node(state: GraphState, config=None) -> dict:
    """Delega ao ai-assistant (A2A) a escolha de placas, profissionais e empresas.

    O JWT do profissional é repassado e a persona vai como `profissional`: o assistente
    então recomenda só com dados públicos, sem unidade nem empresa cadastradas."""
    turn_agents = append_turn_agent(state, "product_advisor")
    token = current_user_token.get()
    if not token:
        return {"messages": [AIMessage(content=_SEM_TOKEN)], "turn_agents": turn_agents}

    thread_id = ((config or {}).get("configurable") or {}).get("thread_id")
    try:
        resultado = await delegate(
            settings.A2A_ASSISTANT_URL,
            _last_user_text(state),
            token=token,
            persona="profissional",
            context_id=thread_id,
        )
    except DelegationError:
        logger.exception("Falha ao delegar ao ai-assistant")
        record_issue(Outcome.TOOL_FAILED, Reason.PRODUCT_ADVISOR_UNAVAILABLE)
        return {
            "messages": [AIMessage(content=_INDISPONIVEL)],
            "turn_agents": turn_agents,
        }

    if (
        resultado.outcome in ("failed", "rejected", "canceled", "unknown")
        or not resultado.text
    ):
        record_issue(Outcome.TOOL_FAILED, Reason.PRODUCT_ADVISOR_UNAVAILABLE)
        return {
            "messages": [AIMessage(content=_INDISPONIVEL)],
            "turn_agents": turn_agents,
        }
    return {"messages": [AIMessage(content=resultado.text)], "turn_agents": turn_agents}
