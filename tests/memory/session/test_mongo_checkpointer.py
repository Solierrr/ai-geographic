import pytest
from pymongo.errors import ServerSelectionTimeoutError

from src.memory.session import mongo_checkpointer


def test_create_mongo_checkpointer_usa_nome_de_colecao_correto(monkeypatch):
    chamadas = []
    monkeypatch.setattr(mongo_checkpointer, "get_mongodb_client", lambda: "cliente-fake")
    monkeypatch.setattr(mongo_checkpointer.settings, "CHECKPOINT_TTL_DIAS", 30)
    monkeypatch.setattr(
        mongo_checkpointer,
        "MongoDBSaver",
        lambda **kw: chamadas.append(kw) or "checkpointer-fake",
    )

    checkpointer = mongo_checkpointer.create_mongo_checkpointer()

    assert checkpointer == "checkpointer-fake"
    kwargs = chamadas[0]
    assert kwargs["client"] == "cliente-fake"
    assert kwargs["db_name"] == "assessor_inteligente"
    assert kwargs["checkpoint_collection_name"] == "checkpoints_conversas"
    assert kwargs["writes_collection_name"] == "checkpoints_conversas_writes"
    # ttl da lib é em segundos, não em dias/minutos
    assert kwargs["ttl"] == 30 * 24 * 60 * 60


def test_create_mongo_checkpointer_retry_sucede_na_terceira_tentativa(monkeypatch):
    monkeypatch.setattr(mongo_checkpointer, "get_mongodb_client", lambda: "cliente-fake")
    monkeypatch.setattr(mongo_checkpointer.time, "sleep", lambda segundos: None)

    chamadas = {"n": 0}

    def mongodb_saver_fake(**kw):
        chamadas["n"] += 1
        if chamadas["n"] < 3:
            raise ServerSelectionTimeoutError("falha intermitente de rede")
        return "checkpointer-fake"

    monkeypatch.setattr(mongo_checkpointer, "MongoDBSaver", mongodb_saver_fake)

    checkpointer = mongo_checkpointer.create_mongo_checkpointer(
        tentativas=3, espera_segundos=0
    )

    assert checkpointer == "checkpointer-fake"
    assert chamadas["n"] == 3


def test_create_mongo_checkpointer_relanca_erro_se_todas_as_tentativas_falharem(
    monkeypatch,
):
    monkeypatch.setattr(mongo_checkpointer, "get_mongodb_client", lambda: "cliente-fake")
    monkeypatch.setattr(mongo_checkpointer.time, "sleep", lambda segundos: None)

    chamadas = {"n": 0}

    def mongodb_saver_fake(**kw):
        chamadas["n"] += 1
        raise ServerSelectionTimeoutError("falha intermitente de rede")

    monkeypatch.setattr(mongo_checkpointer, "MongoDBSaver", mongodb_saver_fake)

    with pytest.raises(ServerSelectionTimeoutError):
        mongo_checkpointer.create_mongo_checkpointer(tentativas=3, espera_segundos=0)

    assert chamadas["n"] == 3
