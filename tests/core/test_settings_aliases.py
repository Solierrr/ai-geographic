from src.core.config.settings import Settings

INFISICAL_NAMES = {
    "DB_MONGO_URI": "mongodb://infisical:27017",
    "GOOGLE_REGISTRY_URL": "http://google-registry:8000",
}
OLD_NAMES = [
    "MONGO_URI",
    "MONGODB_URI",
    "REGISTRY_URL",
]


def test_reads_the_names_used_in_infisical(monkeypatch):
    for name in OLD_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in INFISICAL_NAMES.items():
        monkeypatch.setenv(name, value)

    settings = Settings(_env_file=None)

    assert settings.MONGO_URI == "mongodb://infisical:27017"
    assert settings.REGISTRY_URL == "http://google-registry:8000"


def test_keeps_accepting_the_previous_names(monkeypatch):
    for name in INFISICAL_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MONGODB_URI", "mongodb://antigo:27017")
    monkeypatch.setenv("REGISTRY_URL", "http://localhost:8004")

    settings = Settings(_env_file=None)

    assert settings.MONGO_URI == "mongodb://antigo:27017"
    assert settings.REGISTRY_URL == "http://localhost:8004"
