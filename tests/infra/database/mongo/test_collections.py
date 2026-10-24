from src.infra.database.mongo.collections.collections import Collections


def test_collections_define_mongo_collection_names():
    assert Collections.AGENT_MEMORIES == "agent_memories"
