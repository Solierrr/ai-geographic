from unittest.mock import Mock

from src.agents.base import base_agent


def test_get_default_llm_usa_a_cadeia_de_provedores(monkeypatch):
    cadeia = Mock()
    monkeypatch.setattr(base_agent, "llm_chain", Mock(return_value=cadeia))

    assert base_agent.get_default_llm() is cadeia


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
