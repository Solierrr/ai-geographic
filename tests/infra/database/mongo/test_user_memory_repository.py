import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import src.infra.database.mongo.repositories.user_memory_repository as repo


def test_get_user_memory_retorna_fatos_existentes(monkeypatch):
    collection = Mock()
    collection.find_one = AsyncMock(
        return_value={"user_id": "user-1", "facts": ["mora em SP", "é instalador"]}
    )
    monkeypatch.setattr(repo, "_collection", lambda: collection)

    resultado = asyncio.run(repo.get_user_memory("user-1"))

    assert resultado == ["mora em SP", "é instalador"]
    collection.find_one.assert_awaited_once_with({"user_id": "user-1"})


def test_get_user_memory_retorna_lista_vazia_quando_nao_existe(monkeypatch):
    collection = Mock()
    collection.find_one = AsyncMock(return_value=None)
    monkeypatch.setattr(repo, "_collection", lambda: collection)

    resultado = asyncio.run(repo.get_user_memory("user-novo"))

    assert resultado == []


def test_upsert_user_memory_faz_upsert_com_facts_e_timestamp(monkeypatch):
    collection = Mock()
    collection.update_one = AsyncMock()
    monkeypatch.setattr(repo, "_collection", lambda: collection)

    asyncio.run(repo.upsert_user_memory("user-1", ["mora em SP"]))

    args = collection.update_one.await_args
    assert args.args[0] == {"user_id": "user-1"}
    assert args.args[1]["$set"]["facts"] == ["mora em SP"]
    assert isinstance(args.args[1]["$set"]["updated_at"], datetime)
    assert args.kwargs["upsert"] is True
