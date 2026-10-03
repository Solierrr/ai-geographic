import certifi
from pymongo import AsyncMongoClient

from src.core.config.settings import settings

_client: AsyncMongoClient | None = None


def get_async_mongodb_client() -> AsyncMongoClient:
    global _client
    if _client is None:
        kwargs = {}
        if settings.DB_MONGO_URI.startswith("mongodb+srv://"):
            kwargs["tlsCAFile"] = certifi.where()
        _client = AsyncMongoClient(settings.DB_MONGO_URI, **kwargs)
    return _client
