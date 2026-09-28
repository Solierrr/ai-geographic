import asyncio
from unittest.mock import AsyncMock, Mock

import src.workflow.memory.memory_extraction as extraction_module
from src.workflow.memory.memory_extraction import extrair_fatos_atualizados


def _mock_llm(resposta_texto: str):
    llm = Mock()
    llm.with_fallbacks.return_value = llm
    llm.ainvoke = AsyncMock(return_value=Mock(content=resposta_texto))
    return llm


def test_extrair_fatos_atualizados_trunca_em_20_linhas(monkeypatch):
    resposta = "\n".join(f"fato {i}" for i in range(30))
    llm = _mock_llm(resposta)
    monkeypatch.setattr(extraction_module, "llm_gemini", lambda: llm)
    monkeypatch.setattr(extraction_module, "llm_groq", lambda: Mock())

    resultado = asyncio.run(extrair_fatos_atualizados([], "Usuário: oi\nAssistente: oi"))

    assert len(resultado) == 20
    assert resultado[0] == "fato 0"
    assert resultado[-1] == "fato 19"


def test_extrair_fatos_atualizados_ignora_linhas_vazias(monkeypatch):
    llm = _mock_llm("fato 1\n\n  \nfato 2\n")
    monkeypatch.setattr(extraction_module, "llm_gemini", lambda: llm)
    monkeypatch.setattr(extraction_module, "llm_groq", lambda: Mock())

    resultado = asyncio.run(extrair_fatos_atualizados([], "Usuário: oi\nAssistente: oi"))

    assert resultado == ["fato 1", "fato 2"]


def test_extrair_fatos_atualizados_usa_fallback_do_groq(monkeypatch):
    llm_principal = Mock()
    llm_com_fallback = Mock()
    llm_principal.with_fallbacks.return_value = llm_com_fallback
    llm_com_fallback.ainvoke = AsyncMock(return_value=Mock(content="fato unico"))
    monkeypatch.setattr(extraction_module, "llm_gemini", lambda: llm_principal)
    groq_llm = Mock()
    monkeypatch.setattr(extraction_module, "llm_groq", lambda: groq_llm)

    asyncio.run(extrair_fatos_atualizados([], "Usuário: oi\nAssistente: oi"))

    llm_principal.with_fallbacks.assert_called_once_with([groq_llm])
