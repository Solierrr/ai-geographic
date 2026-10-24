from src.core.config.settings import settings
from src.infra.database.mongo.async_client import get_async_mongodb_client
from src.infra.database.mongo.collections.collections import Collections


async def ensure_user_memory_indexes() -> None:
    collection = get_async_mongodb_client()[settings.DB_MONGO_AGENTS][Collections.AGENT_MEMORIES]
    await collection.create_index("user_id", unique=True)
