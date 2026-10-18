from langgraph.graph import END, StateGraph

from src.memory.session.mongo_checkpointer import create_mongo_checkpointer
from src.workflow.edges import (
    decide_post_input_guardrail,
    decide_post_judge,
    decide_post_router,
)
from src.workflow.nodes.field_conditions_node import field_conditions_node
from src.workflow.nodes.input_guardrail_node import input_guardrail_node
from src.workflow.nodes.judge_node import judge_node
from src.workflow.nodes.orchestrator_node import orchestrator_node
from src.workflow.nodes.output_guardrail_node import output_guardrail_node
from src.workflow.nodes.product_advisor_node import product_advisor_node
from src.workflow.nodes.route_planner_node import route_planner_node
from src.workflow.nodes.router_node import router_node
from src.workflow.nodes.summary_node import condense_history_node
from src.workflow.state import GraphState

graph = StateGraph(GraphState)

graph.add_node("input_guardrail", input_guardrail_node)
graph.add_node("condense_memory", condense_history_node)
graph.add_node("router", router_node)
# Adicione um graph.add_node(...) aqui para cada novo especialista, com o
# mesmo nome usado em `src/workflow/config.py` (SPECIALIST_ROUTES).
graph.add_node("route_planner", route_planner_node)
graph.add_node("field_conditions", field_conditions_node)
graph.add_node("product_advisor", product_advisor_node)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("judge", judge_node)
graph.add_node("output_guardrail", output_guardrail_node)

graph.set_entry_point("input_guardrail")

graph.add_conditional_edges(
    "input_guardrail",
    decide_post_input_guardrail,
    {"proceed": "condense_memory", "end": END},
)

graph.add_edge("condense_memory", "router")

graph.add_conditional_edges(
    "router",
    decide_post_router,
    {
        "route_planner": "route_planner",
        "field_conditions": "field_conditions",
        "product_advisor": "product_advisor",
        "orchestrator": "orchestrator",
        "end": "output_guardrail",
    },
)

graph.add_edge("route_planner", "router")
graph.add_edge("field_conditions", "router")
graph.add_edge("product_advisor", "router")
graph.add_edge("orchestrator", "judge")

graph.add_conditional_edges(
    "judge",
    decide_post_judge,
    {"retry": "orchestrator", "output_guardrail": "output_guardrail"},
)

graph.add_edge("output_guardrail", END)

memory = create_mongo_checkpointer()

compiled_app = graph.compile(checkpointer=memory)
