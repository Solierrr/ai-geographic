import logging

from ai_lib.guardrails import deanonymize_text, parse_output_review
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.prompt import _PROMPT_COMPLIANCE
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

logger = logging.getLogger(__name__)

OUTPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_COMPLIANCE, include_communication_standards=False, include_date=False
)

FALLBACK_RESPONSE = "Não foi possível processar sua solicitação no momento. Tente novamente em instantes."


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
        revisao = parse_output_review(resposta.content)
        if revisao.was_corrected or revisao.revised_response != last_message_text:
            final_text = FALLBACK_RESPONSE
        else:
            final_text = deanonymize_text(last_message_text, state.get("pii_map", {}))
    except Exception as erro:  # noqa: BLE001
        # fail-closed: se o guardrail nao conseguiu revisar, nao deixa a
        # resposta nao revisada sair - troca por uma mensagem generica
        logger.warning("Falha ao avaliar output_guardrail: %s", erro)
        final_text = FALLBACK_RESPONSE

    workflow_steps = append_turn_agent(state, "output_guardrail")
    route_data = None
    if (
        final_text != FALLBACK_RESPONSE
        and state.get("intent") == "route"
        and state.get("route_decision")
    ):
        selected = next(
            (
                route
                for route in state.get("route_options", [])
                if route.get("route_id") == state["route_decision"].get("route_id")
            ),
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
                    "specialists_used": ["route_specialist"]
                    if state.get("intent") == "route" and state.get("route_decision")
                    else [],
                    "workflow_steps": workflow_steps,
                },
            ),
        ],
        "route_data": route_data,
        "output_status": "approved" if final_text != FALLBACK_RESPONSE else "rejected",
        "turn_agents": workflow_steps,
    }
