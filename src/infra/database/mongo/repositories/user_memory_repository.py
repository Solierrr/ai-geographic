from datetime import datetime, timezone

from src.infra.database.mongo.async_client import get_async_mongodb_client
from src.infra.database.mongo.collections.collections import Collections


def _collection():
    return get_async_mongodb_client()["assessor_inteligente"][Collections.AGENT_MEMORIES]


async def get_user_memory(user_id: str) -> list[str]:
    doc = await _collection().find_one({"user_id": user_id})
    return doc["facts"] if doc else []


async def upsert_user_memory(user_id: str, facts: list[str]) -> None:
    await _collection().update_one(
        {"user_id": user_id},
        {"$set": {"facts": facts, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
