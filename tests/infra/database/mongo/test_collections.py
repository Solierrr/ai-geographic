from src.infra.database.mongo.collections.collections import Collections


def test_collections_define_mongo_collection_names():
    assert Collections.CONVERSATIONS == "conversations"
    assert Collections.MESSAGES == "messages"
    assert Collections.AI_LOGS == "ai_logs"
    assert Collections.AGENT_EXECUTIONS == "agent_executions"
    assert Collections.RAG_DOCUMENTS == "rag_documents"
    assert Collections.AGENT_MEMORIES == "agent_memories"
    assert Collections.HALLUCINATION_REVIEWS == "hallucination_reviews"
