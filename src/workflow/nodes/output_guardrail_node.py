import logging

from groq import GroqError
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from pydantic import BaseModel, ValidationError

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.anonymize import deanonymize_text
from src.core.guardrails.prompt import _PROMPT_COMPLIANCE
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

logger = logging.getLogger(__name__)

OUTPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_COMPLIANCE, include_communication_standards=False, include_date=False
)

FALLBACK_RESPONSE = "Não foi possível processar sua solicitação no momento. Tente novamente em instantes."


class RevisaoCompliance(BaseModel):
    resposta_revisada: str
    foi_corrigida: bool


def _parse_revisao_compliance(texto: str) -> RevisaoCompliance:
    """Converte a resposta textual do compliance sem liberar saida invalida."""
    if not isinstance(texto, str):
        raise TypeError("Resposta do compliance nao e texto")

    status: str | None = None
    resposta_linhas: list[str] | None = None
    for linha in texto.splitlines():
        conteudo = linha.strip()
        upper = conteudo.upper()
        if not conteudo:
            if resposta_linhas is not None:
                resposta_linhas.append("")
            continue
        if upper.startswith("STATUS:"):
            if status is not None or resposta_linhas is not None:
                raise ValueError("Marcador STATUS invalido")
            status = conteudo.split(":", 1)[1].strip().upper()
        elif upper.startswith("RESPOSTA:"):
            if status is None or resposta_linhas is not None:
                raise ValueError("Marcador RESPOSTA invalido")
            resposta_linhas = [conteudo.split(":", 1)[1].strip()]
        elif resposta_linhas is not None:
            resposta_linhas.append(linha)
        else:
            raise ValueError("Texto fora do contrato do compliance")

    resposta_revisada = "\n".join(resposta_linhas or []).strip()
    if status not in {"APROVADO", "CORRIGIDO"} or not resposta_revisada:
        raise ValueError("Resposta de compliance incompleta ou invalida")
    return RevisaoCompliance(
        resposta_revisada=resposta_revisada,
        foi_corrigida=status == "CORRIGIDO",
    )


def output_guardrail_node(state: GraphState, config=None) -> dict:
    last_message_text = state["messages"][-1].content
    formatted_prompt = OUTPUT_GUARDRAIL_PROMPT.format(resposta=last_message_text) + (
        "\n\nResponda EXATAMENTE neste formato, em texto (nao chame nenhuma tool):\n"
        "STATUS: APROVADO ou CORRIGIDO\nRESPOSTA: <texto final, ja revisado>"
    )

    try:
        resposta = llm_groq().invoke(
            [HumanMessage(content=formatted_prompt)], config=config
        )
        revisao = _parse_revisao_compliance(resposta.content)
        if revisao.foi_corrigida or revisao.resposta_revisada != last_message_text:
            final_text = FALLBACK_RESPONSE
        else:
            final_text = deanonymize_text(last_message_text, state.get("pii_map", {}))
    except (GroqError, ValidationError, ValueError, TypeError, AttributeError) as erro:
        # fail-closed: se o guardrail nao conseguiu revisar, nao deixa a
        # resposta nao revisada sair - troca por uma mensagem generica
        logger.warning("Falha ao avaliar output_guardrail: %s", erro)
        final_text = FALLBACK_RESPONSE

    workflow_steps = append_turn_agent(state, "output_guardrail")
    route_data = None
    if final_text != FALLBACK_RESPONSE and state.get("intent") == "route" and state.get("route_decision"):
        selected = next(
            (route for route in state.get("route_options", []) if route.get("route_id") == state["route_decision"].get("route_id")),
            None,
        )
        if selected:
            route_data = {
                "route_id": selected["route_id"],
                "duration_seconds": selected["duration_seconds"],
                "distance_meters": selected["distance_meters"],
                "encoded_polyline": selected.get("encoded_polyline"),
                "provider": "google_maps",
            }

    return {
        "messages": [
            RemoveMessage(id=state["messages"][-1].id),
            AIMessage(
                content=final_text,
                additional_kwargs={
                    "specialists_used": ["route_specialist"] if state.get("intent") == "route" and state.get("route_decision") else [],
                    "workflow_steps": workflow_steps,
                },
            ),
        ],
        "route_data": route_data,
        "output_status": "approved" if final_text != FALLBACK_RESPONSE else "rejected",
        "turn_agents": workflow_steps,
    }
