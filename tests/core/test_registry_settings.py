from src.core.config.settings import Settings


def test_registry_url_aceita_o_nome_do_infisical():
    settings = Settings(_env_file=None, GOOGLE_REGISTRY_URL="http://registry.test")

    assert settings.REGISTRY_URL == "http://registry.test"


def test_registry_url_aceita_o_nome_curto():
    settings = Settings(_env_file=None, REGISTRY_URL="http://registry.test")

    assert settings.REGISTRY_URL == "http://registry.test"
