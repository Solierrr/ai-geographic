import asyncio
import json
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

import src.workflow.observability.debug_tracker as debug_tracker
from src.workflow.observability.debug_tracker import DebugTracker, mask_pii


def _meta(node):
    return {"langgraph_node": node}


def _resposta_llm(texto="resposta", model="llama-3.3", tokens_in=10, tokens_out=5):
    message = AIMessage(
        content=texto,
        usage_metadata={
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
        },
        response_metadata={"model_name": model},
    )
    return SimpleNamespace(
        generations=[[SimpleNamespace(message=message)]], llm_output=None
    )


async def _no(tracker, node, run_id, inputs=None, outputs=None, fail=None):
    await tracker.on_chain_start(
        {}, inputs or {}, run_id=run_id, metadata=_meta(node), name=node
    )
    if fail:
        await tracker.on_chain_error(fail, run_id=run_id)
    else:
        await tracker.on_chain_end(outputs or {}, run_id=run_id)


def test_captura_entrada_saida_e_ordem_dos_nos():
    tracker = DebugTracker()

    async def cenario():
        await _no(
            tracker,
            "router",
            "r1",
            inputs={
                "messages": [
                    HumanMessage(content="oi"),
                    HumanMessage(content="placa?"),
                ],
                "route": "",
                "judge_retries": 0,
            },
            outputs={"route": "solar_panel_specialist"},
        )
        await _no(
            tracker,
            "judge",
            "r2",
            outputs={"judge_status": "approved", "judge_retries": 1},
        )

    asyncio.run(cenario())
    debug = tracker.snapshot()

    assert [n["node"] for n in debug["nodes"]] == ["router", "judge"]
    assert [n["order"] for n in debug["nodes"]] == [1, 2]
    router = debug["nodes"][0]
    assert router["status"] == "ok"
    assert router["input"]["message_count"] == 2
    assert router["input"]["last_message"] == {"type": "human", "content": "placa?"}
    assert router["output"] == {"route": "solar_panel_specialist"}
    assert router["duration_ms"] >= 0
    assert debug["route"] == "solar_panel_specialist"
    assert debug["judge"] == {"status": "approved", "retries": 1}
    assert debug["truncated"] is False


def test_ignora_runs_que_nao_sao_nos_do_grafo():
    tracker = DebugTracker()

    async def cenario():
        await tracker.on_chain_start(
            {}, {}, run_id="x", metadata=_meta("router"), name="RunnableSequence"
        )
        await tracker.on_chain_start({}, {}, run_id="y", metadata={}, name="router")

    asyncio.run(cenario())

    assert tracker.snapshot()["nodes"] == []


def test_registra_erro_do_no():
    tracker = DebugTracker()
    asyncio.run(_no(tracker, "router", "r1", fail=ValueError("quebrou")))

    node = tracker.snapshot()["nodes"][0]

    assert node["status"] == "error"
    assert node["error"] == "ValueError: quebrou"
    assert node["output"] is None


def test_mesmo_no_executado_duas_vezes_gera_dois_registros():
    tracker = DebugTracker()

    async def cenario():
        await _no(tracker, "orchestrator", "a", outputs={"n": 1})
        await _no(tracker, "judge", "b", outputs={"judge_status": "retry"})
        await _no(tracker, "orchestrator", "c", outputs={"n": 2})

    asyncio.run(cenario())
    nodes = tracker.snapshot()["nodes"]

    assert [n["node"] for n in nodes] == ["orchestrator", "judge", "orchestrator"]
    assert [n["output"] for n in nodes if n["node"] == "orchestrator"] == [
        {"n": 1},
        {"n": 2},
    ]


def test_chamada_de_llm_fica_no_no_certo_com_tokens_e_modelo():
    tracker = DebugTracker()

    async def cenario():
        await tracker.on_chain_start(
            {}, {}, run_id="n1", metadata=_meta("router"), name="router"
        )
        await tracker.on_chat_model_start(
            {},
            [[HumanMessage(content="qual rota?")]],
            run_id="l1",
            metadata=_meta("router"),
        )
        await tracker.on_llm_end(_resposta_llm("faq_reader"), run_id="l1")
        await tracker.on_chain_end({"route": "faq_reader"}, run_id="n1")

    asyncio.run(cenario())
    call = tracker.snapshot()["nodes"][0]["llm_calls"][0]

    assert call["prompt"] == [{"type": "human", "content": "qual rota?"}]
    assert call["completion"] == "faq_reader"
    assert call["model"] == "llama-3.3"
    assert call["tokens_in"] == 10
    assert call["tokens_out"] == 5
    assert call["latency_ms"] >= 0
    assert call["error"] is None


def test_on_llm_start_e_erro_de_llm():
    tracker = DebugTracker()

    async def cenario():
        await tracker.on_chain_start(
            {}, {}, run_id="n1", metadata=_meta("judge"), name="judge"
        )
        await tracker.on_llm_start(
            {}, ["um prompt"], run_id="l1", metadata=_meta("judge")
        )
        await tracker.on_llm_error(TimeoutError("lento"), run_id="l1")
        await tracker.on_chain_end({}, run_id="n1")

    asyncio.run(cenario())
    call = tracker.snapshot()["nodes"][0]["llm_calls"][0]

    assert call["prompt"] == [{"type": "prompt", "content": "um prompt"}]
    assert call["error"] == "TimeoutError: lento"
    assert call["completion"] is None


def test_llm_fora_de_no_vai_para_a_lista_separada():
    tracker = DebugTracker()

    async def cenario():
        await tracker.on_llm_start({}, ["p"], run_id="l1", metadata={})
        await tracker.on_llm_end(_resposta_llm(), run_id="l1")

    asyncio.run(cenario())
    debug = tracker.snapshot()

    assert debug["nodes"] == []
    assert len(debug["llm_calls_outside_nodes"]) == 1


def test_resposta_de_llm_sem_uso_nao_quebra():
    tracker = DebugTracker()
    resposta = SimpleNamespace(generations=[], llm_output=None)

    async def cenario():
        await tracker.on_llm_start({}, ["p"], run_id="l1", metadata={})
        await tracker.on_llm_end(resposta, run_id="l1")

    asyncio.run(cenario())
    call = tracker.snapshot()["llm_calls_outside_nodes"][0]

    assert call["completion"] == ""
    assert call["tokens_in"] is None
    assert call["model"] is None


def test_pii_map_e_dados_do_usuario_nunca_saem():
    tracker = DebugTracker()
    asyncio.run(
        _no(
            tracker,
            "input_guardrail",
            "r1",
            inputs={"pii_map": {"[PII_CPF_a]": "123.456.789-09"}, "user_id": "u-1"},
            outputs={
                "pii_map": {"[PII_CPF_a]": "123.456.789-09"},
                "user_memory": "- mora em SP",
                "user_id": "u-1",
                "route": "faq_reader",
            },
        )
    )

    texto = json.dumps(tracker.snapshot(), ensure_ascii=False)

    assert "pii_map" not in texto
    assert "123.456.789-09" not in texto
    assert "user_memory" not in texto
    assert "mora em SP" not in texto
    assert "u-1" not in texto
    assert "faq_reader" in texto


def test_anonimiza_cpf_cnpj_telefone_e_email():
    tracker = DebugTracker()
    asyncio.run(
        _no(
            tracker,
            "orchestrator",
            "r1",
            outputs={
                "text": (
                    "CPF 123.456.789-09, CNPJ 12.345.678/0001-95, "
                    "tel (11) 91234-5678, mail joao@exemplo.com"
                )
            },
        )
    )

    texto = tracker.snapshot()["nodes"][0]["output"]["text"]

    assert texto == "CPF [CPF], CNPJ [CNPJ], tel [TELEFONE], mail [EMAIL]"


def test_mask_pii_texto_sem_dados_pessoais_fica_igual():
    assert mask_pii("quero placas solares") == "quero placas solares"


def test_trunca_campo_grande_e_marca_truncated():
    tracker = DebugTracker()
    asyncio.run(_no(tracker, "orchestrator", "r1", outputs={"text": "a" * 10_000}))

    debug = tracker.snapshot()
    texto = debug["nodes"][0]["output"]["text"]

    assert len(texto) == debug_tracker.MAX_FIELD_CHARS + 1
    assert texto.endswith("…")
    assert debug["truncated"] is True


def test_respeita_o_teto_total_de_bytes(monkeypatch):
    monkeypatch.setattr(debug_tracker, "MAX_TOTAL_BYTES", 3000)
    tracker = DebugTracker()

    async def cenario():
        for i in range(40):
            await _no(
                tracker,
                f"no{i}",
                f"r{i}",
                inputs={"route": "x" * 500},
                outputs={"text": "y" * 500},
            )

    asyncio.run(cenario())
    debug = tracker.snapshot()

    assert debug["truncated"] is True
    assert len(debug["nodes"]) == 40
    assert all(node["input"] is None for node in debug["nodes"])


def test_objetos_nao_serializaveis_viram_texto():
    tracker = DebugTracker()
    asyncio.run(_no(tracker, "router", "r1", outputs={"obj": object(), "ok": {1, 2}}))

    saida = tracker.snapshot()["nodes"][0]["output"]

    assert isinstance(saida["obj"], str)
    assert sorted(saida["ok"]) == [1, 2]
    json.dumps(tracker.snapshot())


def test_texto_longo_sem_separadores_e_cortado_rapido():
    """Os padrões de PII são quadráticos; o corte vem antes da anonimização."""
    import time

    collector = DebugTracker()
    collector._orphan_llm.append({"prompt": "y" * 2_000_000})

    inicio = time.perf_counter()
    snapshot = collector.snapshot()

    assert time.perf_counter() - inicio < 5
    assert snapshot["truncated"] is True
