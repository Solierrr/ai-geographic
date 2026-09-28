from langgraph.graph import MessagesState


class GraphState(MessagesState):
    route: str
    turn_agents: list[str]
    summary: str
    pii_map: dict
    judge_retries: int
    judge_status: str
    user_id: str | None
    user_memory: str
