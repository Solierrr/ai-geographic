import asyncio
from unittest.mock import AsyncMock, Mock

import src.infra.database.mongo.indexes.user_memory_indexes as indexes_module


def test_ensure_user_memory_indexes_cria_indice_unico_por_user_id(monkeypatch):
    collection = Mock()
    collection.create_index = AsyncMock()
    client = {"assessor_inteligente": {"agent_memories": collection}}
    monkeypatch.setattr(
        indexes_module, "get_async_mongodb_client", lambda: client
    )

    asyncio.run(indexes_module.ensure_user_memory_indexes())

    collection.create_index.assert_awaited_once_with("user_id", unique=True)
