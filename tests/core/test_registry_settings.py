from src.core.config.settings import Settings


def test_registry_url_usa_o_nome_oficial_do_vault():
    settings = Settings(_env_file=None, GOOGLE_REGISTRY_URL="http://registry.test")

    assert settings.GOOGLE_REGISTRY_URL == "http://registry.test"


def test_registry_url_nao_aceita_alias_curto():
    settings = Settings(_env_file=None, REGISTRY_URL="http://registry.test")

    assert settings.GOOGLE_REGISTRY_URL == "http://localhost:8010"
