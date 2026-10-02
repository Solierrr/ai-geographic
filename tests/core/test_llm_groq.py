import pytest
from ai_lib.llm import LeasedChatModel
from ai_lib.registry import RegistryError

from src.core.config.settings import settings
from src.core.llm import registry as registry_module
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq

MODELOS_DESCONTINUADOS_PELO_GROQ = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
}


@pytest.fixture(autouse=True)
def registry_settings(monkeypatch):
    monkeypatch.setattr(settings, "REGISTRY_URL", "http://registry.test")
    monkeypatch.setattr(settings, "REGISTRY_CONSUMER_TOKEN", "token-de-teste")
    registry_module.registry_client.cache_clear()
    yield
    registry_module.registry_client.cache_clear()


def test_default_nao_usa_modelo_descontinuado():
    """Regressão: llama-3.3-70b-versatile foi descontinuado pelo Groq em
    17/06/2026. Os call sites de llm_groq() dependem do default, sem
    sobrescrever o modelo, então esse teste protege contra alguém
    reintroduzir um modelo fora do catálogo sem perceber."""
    assert llm_groq().model_name not in MODELOS_DESCONTINUADOS_PELO_GROQ


def test_default_e_o_modelo_recomendado_pelo_groq():
    instancia = llm_groq()

    assert isinstance(instancia, LeasedChatModel)
    assert instancia.provider == "groq"
    assert instancia.model_name == "openai/gpt-oss-120b"


def test_ainda_aceita_sobrescrever_o_modelo():
    assert llm_groq(model="outro-modelo-qualquer").model_name == "outro-modelo-qualquer"


def test_gemini_usa_o_corretor_e_o_modelo_padrao():
    instancia = llm_gemini(temperature=0.1)

    assert instancia.provider == "gemini"
    assert instancia.model_name == "gemini-2.5-flash"
    assert instancia.temperature == 0.1


def test_sem_configuracao_do_registry_falha_na_hora(monkeypatch):
    monkeypatch.setattr(settings, "REGISTRY_URL", None)
    registry_module.registry_client.cache_clear()

    with pytest.raises(RegistryError):
        llm_groq()
