from src.core.config.settings import Settings

INFISICAL_NAMES = {
    "DB_MONGO_URI": "mongodb://infisical:27017",
    "UPSTASH_AGENTS_HOST": "agentes.upstash.io",
    "UPSTASH_AGENTS_PORT": "6380",
    "UPSTASH_AGENTS_USERNAME": "agentes",
    "UPSTASH_AGENTS_PASSWORD": "senha-dos-agentes",
    "GOOGLE_REGISTRY_URL": "http://google-registry:8000",
}
OLD_NAMES = [
    "MONGO_URI",
    "MONGODB_URI",
    "UPSTASH_REDIS_HOST",
    "UPSTASH_REDIS_PORT",
    "UPSTASH_REDIS_USERNAME",
    "UPSTASH_REDIS_PASSWORD",
    "REGISTRY_URL",
]


def test_reads_the_names_used_in_infisical(monkeypatch):
    for name in OLD_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in INFISICAL_NAMES.items():
        monkeypatch.setenv(name, value)

    settings = Settings(_env_file=None)

    assert settings.MONGO_URI == "mongodb://infisical:27017"
    assert settings.UPSTASH_REDIS_HOST == "agentes.upstash.io"
    assert settings.UPSTASH_REDIS_PORT == 6380
    assert settings.UPSTASH_REDIS_USERNAME == "agentes"
    assert settings.UPSTASH_REDIS_PASSWORD == "senha-dos-agentes"
    assert settings.REGISTRY_URL == "http://google-registry:8000"


def test_keeps_accepting_the_previous_names(monkeypatch):
    for name in INFISICAL_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MONGODB_URI", "mongodb://antigo:27017")
    monkeypatch.setenv("UPSTASH_REDIS_HOST", "antigo.upstash.io")
    monkeypatch.setenv("REGISTRY_URL", "http://localhost:8004")

    settings = Settings(_env_file=None)

    assert settings.MONGO_URI == "mongodb://antigo:27017"
    assert settings.UPSTASH_REDIS_HOST == "antigo.upstash.io"
    assert settings.REGISTRY_URL == "http://localhost:8004"
