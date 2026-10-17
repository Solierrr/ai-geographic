import pytest

from src.core.llm.llm_groq import llm_groq

MODELOS_DESCONTINUADOS_PELO_GROQ = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
}


@pytest.fixture(autouse=True)
def sem_override_de_modelo(monkeypatch):
    monkeypatch.delenv("LLM_MODEL_GROQ", raising=False)


def test_default_nao_usa_modelo_descontinuado():
    """Regressão: llama-3.3-70b-versatile foi descontinuado pelo Groq em
    17/06/2026. Os call sites de llm_groq() dependem do default, sem
    sobrescrever o modelo, então esse teste protege contra alguém
    reintroduzir um modelo fora do catálogo sem perceber."""
    instancia = llm_groq()
    assert instancia.model_name not in MODELOS_DESCONTINUADOS_PELO_GROQ


def test_default_e_o_modelo_recomendado_pelo_groq():
    instancia = llm_groq()
    assert instancia.model_name == "openai/gpt-oss-120b"


def test_ainda_aceita_sobrescrever_o_modelo():
    instancia = llm_groq(model="outro-modelo-qualquer")
    assert instancia.model_name == "outro-modelo-qualquer"


def test_modelo_pode_vir_da_variavel_de_ambiente(monkeypatch):
    monkeypatch.setenv("LLM_MODEL_GROQ", "modelo-da-variavel")
    assert llm_groq().model_name == "modelo-da-variavel"
