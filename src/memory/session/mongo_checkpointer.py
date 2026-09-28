import time

from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo.errors import ServerSelectionTimeoutError

from src.core.config.settings import settings
from src.infra.database.mongodb_sync_client import get_mongodb_client


def create_mongo_checkpointer(tentativas: int = 3, espera_segundos: float = 2.0) -> MongoDBSaver:
    client = get_mongodb_client()
    ttl_segundos = settings.CHECKPOINT_TTL_DIAS * 24 * 60 * 60  # a lib espera segundos, não dias

    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            return MongoDBSaver(
                client=client,
                db_name="assessor_inteligente",
                checkpoint_collection_name="checkpoints_conversas",
                writes_collection_name="checkpoints_conversas_writes",
                ttl=ttl_segundos,
            )
        except ServerSelectionTimeoutError as erro:
            ultimo_erro = erro
            if tentativa < tentativas:
                time.sleep(espera_segundos)
    raise ultimo_erro
