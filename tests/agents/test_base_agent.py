from unittest.mock import Mock

from src.agents.base import base_agent


def test_get_default_llm_configura_groq_como_fallback(monkeypatch):
    gemini = Mock()
    groq = Mock()
    llm_com_fallback = Mock()
    gemini.with_fallbacks.return_value = llm_com_fallback
    monkeypatch.setattr(base_agent, "llm_gemini", Mock(return_value=gemini))
    monkeypatch.setattr(base_agent, "llm_groq", Mock(return_value=groq))

    resultado = base_agent.get_default_llm()

    assert resultado is llm_com_fallback
    gemini.with_fallbacks.assert_called_once_with([groq])


def test_build_agent_monta_prompt_e_cria_agente(monkeypatch):
    prompt = "PROMPT FINAL"
    llm = Mock()
    agente = Mock()
    build_prompt = Mock(return_value=prompt)
    monkeypatch.setattr(base_agent, "build_system_prompt", build_prompt)
    monkeypatch.setattr(base_agent, "get_default_llm", Mock(return_value=llm))
    monkeypatch.setattr(base_agent, "create_agent", Mock(return_value=agente))

    resultado = base_agent.build_agent(
        "PROMPT ESPECIFICO",
        tools=["ferramenta"],
        include_communication_standards=False,
        user_type="fornecedor",
        user_details={"empresa": "ExemploCorp"},
        include_date=False,
    )

    assert resultado is agente
    build_prompt.assert_called_once_with(
        specific_prompt="PROMPT ESPECIFICO",
        include_communication_standards=False,
        user_type="fornecedor",
        user_details={"empresa": "ExemploCorp"},
        include_date=False,
    )
    base_agent.create_agent.assert_called_once_with(
        model=llm,
        tools=["ferramenta"],
        system_prompt=prompt,
    )
