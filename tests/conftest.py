import pytest

from src.core.config.settings import settings


@pytest.fixture(autouse=True)
def _chat_sem_validacao_de_jwt(monkeypatch):
    """Os testes de rota usam tokens de mentira; a validação do JWT tem testes próprios."""
    monkeypatch.setattr(settings, "JWT_JWKS_URL", None)
    monkeypatch.setattr(settings, "ENVIRONMENT", "LOCAL")
