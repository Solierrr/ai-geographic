import logging

from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.route_planner.route_planner_prompt import ROUTE_PLANNER_AGENT
from src.infra.mcp.client import get_mcp_tools_by_name
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

logger = logging.getLogger(__name__)

_INDISPONIVEL = "Não consegui consultar o mapa agora. Tente novamente em instantes."


async def route_planner_node(state: GraphState, config=None) -> dict:
    turn_agents = append_turn_agent(state, "route_planner")
    try:
        tools = await get_mcp_tools_by_name(
            "resolve_names", "search_places", "compute_routes"
        )
    except Exception:
        logger.exception("Falha ao carregar as tools do MCP do Maps")
        return {
            "messages": [AIMessage(content=_INDISPONIVEL)],
            "turn_agents": turn_agents,
        }

    agent = build_agent(ROUTE_PLANNER_AGENT, tools=tools)
    result = await agent.ainvoke(
        {"messages": messages_with_summary(state)}, config=config
    )
    return {
        "messages": [AIMessage(content=result["messages"][-1].content)],
        "turn_agents": turn_agents,
    }
