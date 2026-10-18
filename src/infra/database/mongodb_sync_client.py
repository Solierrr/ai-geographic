import certifi
from pymongo import MongoClient

from src.core.config.settings import settings


def get_mongodb_client() -> MongoClient:
    """Return a MongoDB client with TLS settings appropriate to its URI."""
    if settings.MONGO_URI.startswith("mongodb+srv://"):
        return MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())

    return MongoClient(settings.MONGO_URI)
