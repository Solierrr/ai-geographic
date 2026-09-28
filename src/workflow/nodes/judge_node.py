import logging

from groq import GroqError
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from pydantic import BaseModel

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.judge.judge_prompt import JUDGE_AGENT
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

logger = logging.getLogger(__name__)

JUDGE_PROMPT = build_system_prompt(JUDGE_AGENT, include_communication_standards=False)

MAX_JUDGE_RETRIES = 1

BLOCKED_RESPONSE = (
    "Não foi possível gerar uma resposta confiável para essa solicitação. "
    "Poderia reformular sua pergunta com mais detalhes?"
)


class VereditoJuiz(BaseModel):
    status: str
    justificativa: str


def _parse_veredito_juiz(texto: str) -> VereditoJuiz:
    """Converte a resposta textual do juiz; formato invalido reprova."""
    if not isinstance(texto, str):
        raise TypeError("Resposta do juiz nao e texto")

    campos: dict[str, str] = {}
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        if ":" not in linha:
            raise ValueError("Linha sem marcador no juiz")
        chave, valor = linha.split(":", 1)
        chave = chave.strip().upper()
        valor = valor.strip()
        if chave not in {"STATUS", "JUSTIFICATIVA"} or chave in campos or not valor:
            raise ValueError("Campo invalido no juiz")
        campos[chave] = valor

    if set(campos) != {"STATUS", "JUSTIFICATIVA"}:
        raise ValueError("Campos obrigatorios ausentes no juiz")
    status = campos["STATUS"].upper()
    if status not in {"APROVADO", "REPROVADO"}:
        raise ValueError("Status desconhecido")
    return VereditoJuiz(status=status, justificativa=campos["JUSTIFICATIVA"])


def judge_node(state: GraphState, config=None) -> dict:
    last_message = state["messages"][-1].content
    messages_with_context = [
        SystemMessage(
            content=(
                JUDGE_PROMPT
                + "\n\nResponda EXATAMENTE neste formato, em texto (nao chame nenhuma tool):\n"
                "STATUS: APROVADO ou REPROVADO\nJUSTIFICATIVA: <texto>"
            )
        ),
        HumanMessage(content=f"Resposta a ser auditada:\n\n{last_message}"),
    ]
    try:
        resposta = llm_groq().invoke(messages_with_context, config=config)
        veredito = _parse_veredito_juiz(resposta.content)
        status = veredito.status
    except (GroqError, ValueError, TypeError, AttributeError) as erro:
        logger.warning("Falha ao avaliar judge: %s", erro)
        status = "REPROVADO"

    retries = state.get("judge_retries", 0)

    if status == "APROVADO":
        return {
            "judge_status": "approved",
            "turn_agents": append_turn_agent(state, "judge_approved"),
        }

    if retries < MAX_JUDGE_RETRIES:
        return {
            "messages": [RemoveMessage(id=state["messages"][-1].id)],
            "judge_status": "retry",
            "judge_retries": retries + 1,
            "turn_agents": append_turn_agent(state, "judge_rejected"),
        }

    return {
        "messages": [
            RemoveMessage(id=state["messages"][-1].id),
            AIMessage(content=BLOCKED_RESPONSE),
        ],
        "judge_status": "blocked",
        "turn_agents": append_turn_agent(state, "judge_blocked"),
    }
