import pytest

from src.core.llm.llm_chain import llm_chain
from src.core.llm.llm_openai import llm_openai


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch):
    for name in ("LLM_PROVIDER_ORDER", "LLM_MODEL_OPENAI"):
        monkeypatch.delenv(name, raising=False)
    for provider in ("GEMINI", "GROQ", "OPENAI"):
        monkeypatch.setenv(f"{provider}_API_KEY", "chave-falsa")


def test_cadeia_segue_a_ordem_configurada(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER_ORDER", "openai,groq")
    monkeypatch.setenv("LLM_MODEL_OPENAI", "gpt-6-luna")

    cadeia = llm_chain()

    assert cadeia.runnable.provider == "openai"
    assert [m.provider for m in cadeia.fallbacks] == ["groq"]


def test_openai_usa_o_modelo_da_variavel(monkeypatch):
    monkeypatch.setenv("LLM_MODEL_OPENAI", "gpt-6-luna")
    assert llm_openai().model_name == "gpt-6-luna"


def test_openai_sem_modelo_configurado_falha_claramente():
    with pytest.raises(ValueError, match="LLM_MODEL_OPENAI"):
        llm_openai()
