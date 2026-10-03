from langgraph.graph import END, StateGraph

from src.memory.session.mongo_checkpointer import create_mongo_checkpointer
from src.workflow.edges import decide_post_input_guardrail
from src.workflow.edges.routing_edges import (
    decide_judge_retry,
    decide_post_location,
    decide_post_orchestrator,
    decide_post_routes,
)
from src.workflow.nodes.input_guardrail_node import input_guardrail_node
from src.workflow.nodes.judge_node import judge_node
from src.workflow.nodes.location_node import resolve_locations_node
from src.workflow.nodes.orchestrator_node import orchestrator_node
from src.workflow.nodes.output_guardrail_node import output_guardrail_node
from src.workflow.nodes.route_specialist_node import route_specialist_node
from src.workflow.nodes.routes_node import routes_node
from src.workflow.nodes.solar_node import solar_node
from src.workflow.nodes.summary_node import condense_history_node
from src.workflow.nodes.timezone_node import timezone_node
from src.workflow.nodes.weather_node import weather_node
from src.workflow.state import GraphState

graph = StateGraph(GraphState)

graph.add_node("input_guardrail", input_guardrail_node)
graph.add_node("condense_memory", condense_history_node)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("location", resolve_locations_node)
graph.add_node("routes", routes_node)
graph.add_node("weather", weather_node)
graph.add_node("solar", solar_node)
graph.add_node("timezone", timezone_node)
graph.add_node("route_specialist", route_specialist_node)
graph.add_node("judge", judge_node)
graph.add_node("output_guardrail", output_guardrail_node)

graph.set_entry_point("input_guardrail")

graph.add_conditional_edges(
    "input_guardrail",
    decide_post_input_guardrail,
    {"proceed": "condense_memory", "end": END},
)

graph.add_edge("condense_memory", "orchestrator")
graph.add_conditional_edges(
    "orchestrator",
    decide_post_orchestrator,
    {"resolve": "location", "respond": "output_guardrail"},
)
graph.add_conditional_edges(
    "location",
    decide_post_location,
    {
        "routes": "routes",
        "solar": "solar",
        "timezone": "timezone",
        "respond": "output_guardrail",
    },
)
graph.add_edge("solar", "output_guardrail")
graph.add_edge("timezone", "output_guardrail")
graph.add_conditional_edges(
    "routes",
    decide_post_routes,
    {"weather": "weather", "respond": "output_guardrail"},
)
graph.add_edge("weather", "route_specialist")
graph.add_edge("route_specialist", "output_guardrail")
graph.add_edge("output_guardrail", "judge")

graph.add_conditional_edges(
    "judge",
    decide_judge_retry,
    {"specialist": "route_specialist", "orchestrator": "orchestrator", "end": END},
)

memory = create_mongo_checkpointer()

compiled_app = graph.compile(checkpointer=memory)
