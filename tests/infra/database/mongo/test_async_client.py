from src.infra.database.mongo import async_client


def test_async_client_does_not_force_tls_for_local_mongodb(monkeypatch):
    calls = []

    monkeypatch.setattr(async_client, "_client", None)
    monkeypatch.setattr(
        async_client.settings, "DB_MONGO_URI", "mongodb://localhost:27017"
    )
    monkeypatch.setattr(
        async_client,
        "AsyncMongoClient",
        lambda uri, **kwargs: calls.append((uri, kwargs)) or "client",
    )

    assert async_client.get_async_mongodb_client() == "client"
    assert calls == [("mongodb://localhost:27017", {})]


def test_async_client_uses_ca_bundle_for_srv_uri(monkeypatch):
    calls = []
    uri = "mongodb+srv://user:password@example.mongodb.net/database"

    monkeypatch.setattr(async_client, "_client", None)
    monkeypatch.setattr(async_client.settings, "DB_MONGO_URI", uri)
    monkeypatch.setattr(async_client.certifi, "where", lambda: "ca-bundle.pem")
    monkeypatch.setattr(
        async_client,
        "AsyncMongoClient",
        lambda value, **kwargs: calls.append((value, kwargs)) or "client",
    )

    assert async_client.get_async_mongodb_client() == "client"
    assert calls == [(uri, {"tlsCAFile": "ca-bundle.pem"})]
