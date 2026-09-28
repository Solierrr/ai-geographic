import certifi
from pymongo import AsyncMongoClient

from src.core.config.settings import settings

_client: AsyncMongoClient | None = None


def get_async_mongodb_client() -> AsyncMongoClient:
    global _client
    if _client is None:
        _client = AsyncMongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    return _client
