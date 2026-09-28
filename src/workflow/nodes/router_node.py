from groq import GroqError
from langchain_core.messages import AIMessage, SystemMessage
from pydantic import BaseModel

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.router.router_prompt import ROUTER_AGENT
from src.core.llm.llm_groq import llm_groq
from src.workflow import config
from src.workflow.edges.routing_edges import (
    available_specialist_routes,
    consulted_specialists,
)
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

ROUTER_PROMPT = build_system_prompt(ROUTER_AGENT)


class DecisaoRoteamento(BaseModel):
    rota: str | None  # None = responder direto, sem especialista
    resposta_direta: str | None = None


def _parse_decisao_roteamento(texto: str) -> DecisaoRoteamento:
    """Converte o contrato textual do roteador em uma decisao validavel."""
    if not isinstance(texto, str):
        raise TypeError("Resposta do roteador nao e texto")

    rota: str | None = None
    resposta_direta_linhas: list[str] | None = None
    marcador_rota_encontrado = False

    for linha in texto.splitlines():
        conteudo = linha.strip()
        upper = conteudo.upper()
        if not conteudo:
            if resposta_direta_linhas is not None:
                resposta_direta_linhas.append("")
            continue
        if upper.startswith("ROTA:"):
            if marcador_rota_encontrado or resposta_direta_linhas is not None:
                raise ValueError("Marcador ROTA invalido")
            valor = conteudo.split(":", 1)[1].strip()
            rota = None if not valor or valor.upper() == "NONE" else valor.lower()
            marcador_rota_encontrado = True
        elif upper.startswith("RESPOSTA_DIRETA:"):
            if not marcador_rota_encontrado or resposta_direta_linhas is not None:
                raise ValueError("Marcador RESPOSTA_DIRETA invalido")
            resposta_direta_linhas = [conteudo.split(":", 1)[1].strip()]
        elif resposta_direta_linhas is not None:
            resposta_direta_linhas.append(linha)
        else:
            raise ValueError("Texto fora do contrato do roteador")

    if not marcador_rota_encontrado or resposta_direta_linhas is None:
        raise ValueError("Campos obrigatorios ausentes no roteador")

    resposta_direta = "\n".join(resposta_direta_linhas).strip() or None
    if rota is None and resposta_direta is None:
        raise ValueError("Resposta direta ausente")
    return DecisaoRoteamento(rota=rota, resposta_direta=resposta_direta)


def router_node(state: GraphState, runnable_config=None) -> dict:
    consulted = consulted_specialists(state)
    available_routes = sorted(available_specialist_routes(state))
    limit_reached = len(consulted) >= config.MAX_SPECIALISTS_PER_REQUEST

    if consulted and (limit_reached or not available_routes):
        return {
            "route": "orchestrator",
            "turn_agents": append_turn_agent(state, "router"),
        }

    routing_context = (
        "Rotas disponiveis nesta solicitacao: "
        f"{', '.join(available_routes) or 'nenhuma'}.\n"
        "Se as respostas ja reunidas na conversa forem suficientes para "
        "responder ao usuario, preencha rota=orchestrator.\n"
        "Caso contrario, preencha rota com uma das rotas disponiveis acima.\n"
        "Se nenhuma rota for necessaria e voce puder responder diretamente, "
        "deixe rota vazia (None) e preencha resposta_direta.\n\n"
        "Responda EXATAMENTE neste formato, em texto (nao chame nenhuma tool):\n"
        "ROTA: <nome_da_rota, orchestrator ou None>\n"
        "RESPOSTA_DIRETA: <texto ou vazio>"
    )
    messages_with_context = [
        SystemMessage(content=ROUTER_PROMPT),
        SystemMessage(content=routing_context),
        *messages_with_summary(state),
    ]
    try:
        resposta = llm_groq().invoke(messages_with_context, config=runnable_config)
        decisao = _parse_decisao_roteamento(resposta.content)
    except (GroqError, ValueError, TypeError, AttributeError):
        # O orquestrador consegue compor uma resposta a partir do contexto;
        # e preferivel a encerrar silenciosamente com uma saida malformada.
        return {
            "route": "orchestrator",
            "turn_agents": append_turn_agent(state, "router_invalid_response"),
        }

    if decisao.rota:
        rotas_permitidas = set(available_routes) | {"orchestrator"}
        if decisao.rota not in rotas_permitidas:
            return {
                "route": "orchestrator",
                "turn_agents": append_turn_agent(state, "router_invalid_route"),
            }
        return {
            "route": decisao.rota.strip().lower(),
            "turn_agents": append_turn_agent(state, "router"),
        }

    return {
        "messages": [AIMessage(content=decisao.resposta_direta or "")],
        "route": "end",
        "turn_agents": append_turn_agent(state, "router_direct_response"),
    }
