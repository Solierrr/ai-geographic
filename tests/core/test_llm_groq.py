import pytest

from src.core.config.settings import settings
from src.core.llm.llm_groq import llm_groq

MODELOS_DESCONTINUADOS_PELO_GROQ = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
}


@pytest.fixture(autouse=True)
def fake_groq_api_key(monkeypatch):
    """ChatGroq valida a api_key já na construção do client, antes de
    qualquer chamada de rede. No CI não existe GROQ_API_KEY configurada,
    então precisamos de uma key falsa só pra passar da validação."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "fake-key-for-tests")


def test_default_nao_usa_modelo_descontinuado():
    """Regressão: llama-3.3-70b-versatile foi descontinuado pelo Groq em
    17/06/2026. Os 7 call sites de llm_groq() no projeto dependem do
    default, sem sobrescrever o modelo, então esse teste protege contra
    alguém reintroduzir um modelo fora do catálogo sem perceber."""
    instancia = llm_groq()
    assert instancia.model_name not in MODELOS_DESCONTINUADOS_PELO_GROQ


def test_default_e_o_modelo_recomendado_pelo_groq():
    instancia = llm_groq()
    assert instancia.model_name == "openai/gpt-oss-120b"


def test_ainda_aceita_sobrescrever_o_modelo():
    instancia = llm_groq(model="outro-modelo-qualquer")
    assert instancia.model_name == "outro-modelo-qualquer"
