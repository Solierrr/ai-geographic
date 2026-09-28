import logging
import time
from datetime import datetime, timezone

from groq import APITimeoutError, RateLimitError
from httpx import ConnectError, TimeoutException
from langchain_core.callbacks import AsyncCallbackHandler

from src.core.config.model_pricing import get_pricing
from src.infra.api_messenger.client import enviar_observabilidade

logger = logging.getLogger(__name__)


def _categorizar_erro_llm(error: Exception) -> str:
    if isinstance(error, RateLimitError):
        return "rate_limited"
    if isinstance(error, APITimeoutError):
        return "timeout"
    return "error"


def _calcular_custo_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    preco = get_pricing(model)
    custo = (tokens_in / 1000) * preco["in"] + (tokens_out / 1000) * preco["out"]
    return round(custo, 6)


def _categorizar_erro_tool(error: Exception) -> str:
    if isinstance(error, TimeoutException):
        return "timeout"
    if isinstance(error, ConnectError):
        return "connection_error"
    return "error"


class StepTracker(AsyncCallbackHandler):
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.step_order = 0
        self._starts = {}
        self._node_by_run = {}
        self._tool_name_by_run = {}

    def _next_order(self) -> int:
        self.step_order += 1
        return self.step_order

    async def _salvar(self, node: str, doc: dict) -> None:
        doc = {
            "conversationId": self.conversation_id,
            "node": node,
            "stepOrder": self._next_order(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **doc,
        }
        try:
            await enviar_observabilidade(doc)
        except Exception as erro:  # noqa: BLE001
            # observabilidade nunca pode derrubar o fluxo principal
            logger.warning("Falha ao enviar observabilidade (node=%s): %s", node, erro)

    async def on_llm_start(
        self, serialized, prompts, *, run_id, metadata=None, **kwargs
    ):
        self._starts[run_id] = time.perf_counter()
        self._node_by_run[run_id] = (metadata or {}).get(
            "langgraph_node", "desconhecido"
        )

    async def on_llm_end(self, response, *, run_id, **kwargs):
        latency_ms = (
            time.perf_counter() - self._starts.pop(run_id, time.perf_counter())
        ) * 1000
        node = self._node_by_run.pop(run_id, "desconhecido")
        generation = response.generations[0][0]
        message = getattr(generation, "message", None)
        usage = getattr(message, "usage_metadata", None) if message else None
        resp_metadata = getattr(message, "response_metadata", {}) if message else {}

        model = (
            resp_metadata.get("model_name")
            or resp_metadata.get("model")
            or "desconhecido"
        )
        tokens_in = usage.get("input_tokens", 0) if usage else 0
        tokens_out = usage.get("output_tokens", 0) if usage else 0
        tokens_total = (usage.get("total_tokens") if usage else None) or (
            tokens_in + tokens_out
        )

        cost_usd = _calcular_custo_usd(model, tokens_in, tokens_out)

        await self._salvar(
            node,
            {
                "stepType": "LLM_CALL",
                "model": model,
                "tokensIn": tokens_in,
                "tokensOut": tokens_out,
                "tokensTotal": tokens_total,
                "costUsd": cost_usd,
                "latencyMs": round(latency_ms, 1),
                "status": "ok",
            },
        )

    async def on_llm_error(self, error, *, run_id, **kwargs):
        latency_ms = (
            time.perf_counter() - self._starts.pop(run_id, time.perf_counter())
        ) * 1000
        node = self._node_by_run.pop(run_id, "desconhecido")
        await self._salvar(
            node,
            {
                "stepType": "LLM_CALL",
                "model": "desconhecido",
                "tokensIn": 0,
                "tokensOut": 0,
                "tokensTotal": 0,
                "costUsd": 0.0,
                "latencyMs": round(latency_ms, 1),
                "status": _categorizar_erro_llm(error),
                "error": str(error),
            },
        )

    async def on_tool_start(
        self, serialized, input_str, *, run_id, metadata=None, **kwargs
    ):
        self._starts[run_id] = time.perf_counter()
        self._node_by_run[run_id] = (metadata or {}).get(
            "langgraph_node", "desconhecido"
        )
        self._tool_name_by_run[run_id] = serialized.get("name", "tool_desconhecida")

    async def on_tool_end(self, output, *, run_id, **kwargs):
        latency_ms = (
            time.perf_counter() - self._starts.pop(run_id, time.perf_counter())
        ) * 1000
        node = self._node_by_run.pop(run_id, "desconhecido")
        tool_name = self._tool_name_by_run.pop(run_id, "tool_desconhecida")
        await self._salvar(
            node,
            {
                "stepType": "TOOL_CALL",
                "toolName": tool_name,
                # tool_call não usa LLM, mas o DTO do api-messenger exige
                # esses campos independente do stepType
                "model": "n/a",
                "tokensIn": 0,
                "tokensOut": 0,
                "tokensTotal": 0,
                "costUsd": 0.0,
                "latencyMs": round(latency_ms, 1),
                "status": "ok",
            },
        )

    async def on_tool_error(self, error, *, run_id, **kwargs):
        latency_ms = (
            time.perf_counter() - self._starts.pop(run_id, time.perf_counter())
        ) * 1000
        node = self._node_by_run.pop(run_id, "desconhecido")
        tool_name = self._tool_name_by_run.pop(run_id, "tool_desconhecida")
        await self._salvar(
            node,
            {
                "stepType": "TOOL_CALL",
                "toolName": tool_name,
                "model": "n/a",
                "tokensIn": 0,
                "tokensOut": 0,
                "tokensTotal": 0,
                "costUsd": 0.0,
                "latencyMs": round(latency_ms, 1),
                "status": _categorizar_erro_tool(error),
                "error": str(error),
            },
        )
