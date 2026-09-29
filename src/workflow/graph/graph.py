from langgraph.graph import END, StateGraph

from src.memory.session.mongo_checkpointer import create_mongo_checkpointer
from src.workflow.edges import (
    decide_post_input_guardrail,
    decide_post_judge,
)
from src.workflow.nodes.input_guardrail_node import input_guardrail_node
from src.workflow.nodes.judge_node import judge_node
from src.workflow.nodes.orchestrator_node import orchestrator_node
from src.workflow.nodes.output_guardrail_node import output_guardrail_node
from src.workflow.nodes.summary_node import condense_history_node
from src.workflow.state import GraphState

graph = StateGraph(GraphState)

graph.add_node("input_guardrail", input_guardrail_node)
graph.add_node("condense_memory", condense_history_node)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("judge", judge_node)
graph.add_node("output_guardrail", output_guardrail_node)

graph.set_entry_point("input_guardrail")

graph.add_conditional_edges(
    "input_guardrail",
    decide_post_input_guardrail,
    {"proceed": "condense_memory", "end": END},
)

graph.add_edge("condense_memory", "orchestrator")
graph.add_edge("orchestrator", "judge")

graph.add_conditional_edges(
    "judge",
    decide_post_judge,
    {"retry": "orchestrator", "output_guardrail": "output_guardrail"},
)

graph.add_edge("output_guardrail", END)

memory = create_mongo_checkpointer()

compiled_app = graph.compile(checkpointer=memory)
