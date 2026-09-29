from unittest.mock import Mock

from groq import GroqError
from langchain_core.messages import AIMessage, RemoveMessage

from src.agents.base.system_prompt import (
    SYSTEM_CORE_COMMUNICATION,
    SYSTEM_CORE_SECURITY,
)
from src.workflow.nodes import output_guardrail_node


def _mock_llm(response, corrected=False):
    llm = Mock()
    status = "CORRIGIDO" if corrected else "APROVADO"
    llm.invoke.return_value = AIMessage(content=f"STATUS: {status}\nRESPOSTA: {response}")
    return llm


def _state(message_id="msg-1"):
    return {
        "messages": [AIMessage(content="Resposta do agente", id=message_id)],
        "pii_map": {"[PII_NOME]": "Ana"},
        "turn_agents": ["input_guardrail_approved", "orchestrator"],
    }


def test_output_guardrail_prompt_omits_communication_standards():
    assert SYSTEM_CORE_SECURITY.strip() in output_guardrail_node.OUTPUT_GUARDRAIL_PROMPT
    assert SYSTEM_CORE_COMMUNICATION.strip() not in output_guardrail_node.OUTPUT_GUARDRAIL_PROMPT


def test_output_guardrail_deanonymizes_valid_response(monkeypatch):
    llm = _mock_llm("Ola, [PII_NOME].", corrected=True)
    deanonymize = Mock(return_value="Ola, Ana.")
    monkeypatch.setattr(output_guardrail_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(output_guardrail_node, "deanonymize_text", deanonymize)
    result = output_guardrail_node.output_guardrail_node(_state())
    assert isinstance(result["messages"][0], RemoveMessage)
    assert result["messages"][1].content == "Ola, Ana."
    assert result["messages"][1].additional_kwargs["specialists_used"] == []
    deanonymize.assert_called_once_with("Ola, [PII_NOME].", {"[PII_NOME]": "Ana"})
    llm.with_structured_output.assert_not_called()


def test_output_guardrail_preserves_approved_response(monkeypatch):
    llm = _mock_llm("Resposta revisada")
    deanonymize = Mock(return_value="Resposta revisada")
    monkeypatch.setattr(output_guardrail_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(output_guardrail_node, "deanonymize_text", deanonymize)

    result = output_guardrail_node.output_guardrail_node(_state("msg-2"))

    assert result["messages"][1].content == "Resposta revisada"
    deanonymize.assert_called_once_with("Resposta revisada", {"[PII_NOME]": "Ana"})


def test_output_guardrail_fails_closed_when_groq_raises(monkeypatch):
    llm = Mock()
    llm.invoke.side_effect = GroqError("groq indisponivel")
    deanonymize = Mock()
    monkeypatch.setattr(output_guardrail_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(output_guardrail_node, "deanonymize_text", deanonymize)
    result = output_guardrail_node.output_guardrail_node(_state())
    assert result["messages"][1].content == output_guardrail_node.FALLBACK_RESPONSE
    deanonymize.assert_not_called()


def test_output_guardrail_fails_closed_for_malformed_response(monkeypatch):
    llm = Mock()
    llm.invoke.return_value = AIMessage(content="STATUS: APROVADO")
    deanonymize = Mock()
    monkeypatch.setattr(output_guardrail_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(output_guardrail_node, "deanonymize_text", deanonymize)
    result = output_guardrail_node.output_guardrail_node(_state())
    assert result["messages"][1].content == output_guardrail_node.FALLBACK_RESPONSE
    deanonymize.assert_not_called()


def test_output_guardrail_fails_closed_for_unknown_status(monkeypatch):
    llm = Mock()
    llm.invoke.return_value = AIMessage(content="STATUS: INDEFINIDO\nRESPOSTA: texto")
    deanonymize = Mock()
    monkeypatch.setattr(output_guardrail_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(output_guardrail_node, "deanonymize_text", deanonymize)

    result = output_guardrail_node.output_guardrail_node(_state("msg-3"))

    assert result["messages"][1].content == output_guardrail_node.FALLBACK_RESPONSE
    deanonymize.assert_not_called()


def test_output_guardrail_parser_preserves_multiline_response():
    review = output_guardrail_node._parse_revisao_compliance(
        "STATUS: CORRIGIDO\nRESPOSTA: Primeira linha.\nSegunda linha."
    )
    assert review.foi_corrigida is True
    assert review.resposta_revisada == "Primeira linha.\nSegunda linha."
