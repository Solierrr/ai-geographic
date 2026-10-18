from unittest.mock import Mock

from groq import GroqError
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)

from src.workflow.nodes import judge_node


def _mock_llm(status, justification="justificativa qualquer"):
    llm = Mock()
    llm.invoke.return_value = AIMessage(
        content=f"STATUS: {status}\nJUSTIFICATIVA: {justification}"
    )
    return llm


def test_judge_approves_valid_response(monkeypatch):
    llm = _mock_llm("APROVADO", "resposta coerente")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))
    result = judge_node.judge_node(
        {"messages": [AIMessage(content="Resposta final", id="msg-1")]}
    )
    assert result["judge_status"] == "approved"
    assert result["turn_agents"] == ["judge_approved"]
    messages = llm.invoke.call_args.args[0]
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert "STATUS:" in messages[0].content
    llm.with_structured_output.assert_not_called()


def test_judge_retries_once_when_rejected(monkeypatch):
    llm = _mock_llm("REPROVADO")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))
    result = judge_node.judge_node(
        {"messages": [AIMessage(content="Resposta", id="msg-2")], "judge_retries": 0}
    )
    assert result["judge_status"] == "retry"
    assert result["judge_retries"] == 1
    assert isinstance(result["messages"][0], RemoveMessage)


def test_judge_blocks_after_retries(monkeypatch):
    llm = _mock_llm("REPROVADO")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))
    result = judge_node.judge_node(
        {"messages": [AIMessage(content="Resposta", id="msg-3")], "judge_retries": 1}
    )
    assert result["judge_status"] == "blocked"
    assert result["messages"][1].content == judge_node.BLOCKED_RESPONSE


def test_judge_retries_for_malformed_response(monkeypatch):
    llm = Mock()
    llm.invoke.return_value = AIMessage(content="Parece uma boa resposta")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))
    result = judge_node.judge_node(
        {"messages": [AIMessage(content="Resposta", id="msg-4")], "judge_retries": 0}
    )
    assert result["judge_status"] == "retry"


def test_judge_retries_when_groq_fails(monkeypatch):
    llm = Mock()
    llm.invoke.side_effect = GroqError("groq indisponivel")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))
    result = judge_node.judge_node(
        {"messages": [AIMessage(content="Resposta", id="msg-5")], "judge_retries": 0}
    )
    assert result["judge_status"] == "retry"
