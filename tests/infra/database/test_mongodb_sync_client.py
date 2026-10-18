from src.infra.database import mongodb_sync_client


def test_get_mongodb_client_usa_uri_local_sem_tls(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        mongodb_sync_client, "MongoClient", lambda *a, **kw: chamadas.append((a, kw))
    )
    monkeypatch.setattr(
        mongodb_sync_client.settings, "MONGO_URI", "mongodb://test-host:27017"
    )

    mongodb_sync_client.get_mongodb_client()

    args, kwargs = chamadas[0]
    assert args == ("mongodb://test-host:27017",)
    assert "tlsCAFile" not in kwargs


def test_get_mongodb_client_usa_ca_para_atlas(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        mongodb_sync_client, "MongoClient", lambda *a, **kw: chamadas.append((a, kw))
    )
    monkeypatch.setattr(
        mongodb_sync_client.settings,
        "MONGO_URI",
        "mongodb+srv://test-host.example",
    )

    mongodb_sync_client.get_mongodb_client()

    args, kwargs = chamadas[0]
    assert args == ("mongodb+srv://test-host.example",)
    assert kwargs["tlsCAFile"]
