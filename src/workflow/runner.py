import asyncio
import logging
from collections.abc import Sequence
from uuid import uuid4

from langchain_core.messages import HumanMessage

from src.core.guardrails.anonymize import anonymize_text
from src.core.security.jwt import decode_user_id
from src.core.security.request_context import current_user_token
from src.infra.api_messenger.client import (
    criar_conversa_chatbot,
    enviar_mensagem_chatbot,
    enviar_mensagem_usuario,
)
from src.infra.database.mongo.repositories.user_memory_repository import (
    get_user_memory,
    upsert_user_memory,
)
from src.workflow.debug_replay import count_turns, run_single_node
from src.workflow.memory.memory_extraction import extrair_fatos_atualizados
from src.workflow.observability.step_tracker import StepTracker
from src.workflow.outcome import resolve_outcome, start_turn

logger = logging.getLogger(__name__)

ASSISTANT_ID = "geographic"
_conversations_por_thread: dict[str, str] = {}
_background_tasks: set[asyncio.Task] = set()


async def _atualizar_memoria(
    user_id: str, fatos_existentes: list[str], ultima_troca: str
) -> None:
    try:
        novos_fatos = await extrair_fatos_atualizados(fatos_existentes, ultima_troca)
        await upsert_user_memory(user_id, novos_fatos)
    except Exception:
        logger.warning(
            "Falha ao atualizar memória de longo prazo (user_id=%s)",
            user_id,
            exc_info=True,
        )


def _agendar_atualizacao_memoria(
    user_id: str, fatos_existentes: list[str], ultima_troca: str
) -> None:
    task = asyncio.create_task(
        _atualizar_memoria(user_id, fatos_existentes, ultima_troca)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _get_or_create_conversation_id(
    thread_id: str, user_token: str, user_details: dict | None = None
) -> str:
    """Reaproveita, por thread_id, a conversa já aberta no api-messenger;
    cria uma nova na primeira mensagem do turno."""
    conversation_id = _conversations_por_thread.get(thread_id)
    if conversation_id is None:
        conversation_id = await criar_conversa_chatbot(
            "lead", user_details or {}, user_token=user_token
        )
        _conversations_por_thread[thread_id] = conversation_id
    return conversation_id


async def _thread_turn(workflow, thread_id: str) -> int | None:
    try:
        return await count_turns(workflow, thread_id) - 1
    except Exception:  # noqa: BLE001
        logger.warning("Não foi possível contar os turnos de %s", thread_id)
        return None


async def execute_turn(
    conversation_id: str,
    user_input: str,
    workflow,
    user_token: str,
    *,
    persist: bool = True,
    save_history: bool = False,
    extra_callbacks: Sequence = (),
) -> dict:
    """Roda um turno do grafo.

    `persist=False` (modo debug) não lê nem atualiza a memória de longo prazo e, por
    padrão, não cria conversa nem grava mensagens e steps no api-messenger.
    `save_history=True` mantém o modo debug mas grava conversa, mensagens e steps
    no api-messenger."""
    saves = persist or save_history
    current_user_token.set(user_token)
    issues = start_turn()
    turn_id = str(uuid4())
    tracker: StepTracker | None = None
    if saves:
        anonymized_user_input, _ = anonymize_text(user_input)
        api_conversation_id = await _get_or_create_conversation_id(
            conversation_id,
            user_token,
            {
                "assistant": ASSISTANT_ID,
                "source": "chat" if persist else "debug",
                "threadId": conversation_id,
            },
        )

        await enviar_mensagem_usuario(
            api_conversation_id, anonymized_user_input, user_token
        )

        tracker = StepTracker(conversation_id=api_conversation_id, issues=issues)

    user_id = await asyncio.to_thread(decode_user_id, user_token)
    fatos_existentes = await get_user_memory(user_id) if persist and user_id else []
    user_memory = "\n".join(f"- {fato}" for fato in fatos_existentes)

    final_state = await workflow.ainvoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "route": "",
            "pii_map": {},
            "turn_agents": [],
            "judge_retries": 0,
            "user_id": user_id,
            "user_memory": user_memory,
        },
        config={
            "configurable": {"thread_id": conversation_id},
            "callbacks": [*([tracker] if tracker else []), *extra_callbacks],
        },
    )

    final_message = final_state["messages"][-1]
    outcome, reason = resolve_outcome(
        final_message.additional_kwargs.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
        issues,
    )
    if not saves:
        return {**final_state, "outcome": outcome, "reason": reason}

    anonymized_assistant_response, _ = anonymize_text(final_message.content)
    message_metadata = final_message.additional_kwargs
    thread_turn = None if persist else await _thread_turn(workflow, conversation_id)
    audit_metadata = {
        "turnId": turn_id,
        "contentAnonymized": True,
        "specialistsUsed": message_metadata.get("specialists_used", []),
        "workflowSteps": message_metadata.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
        **({} if thread_turn is None else {"threadTurn": thread_turn}),
    }
    await enviar_mensagem_chatbot(
        api_conversation_id, anonymized_assistant_response, audit_metadata
    )

    if persist and user_id:
        ultima_troca = f"Usuário: {user_input}\nAssistente: {final_message.content}"
        _agendar_atualizacao_memoria(user_id, fatos_existentes, ultima_troca)

    return {**final_state, "outcome": outcome, "reason": reason}


async def execute_single_node(
    thread_id: str,
    workflow,
    user_token: str,
    *,
    turn: int,
    node: str,
    occurrence: int,
    overrides: dict[int, dict[int, str]],
    extra_callbacks: Sequence = (),
):
    current_user_token.set(user_token)
    return await run_single_node(
        workflow,
        thread_id,
        turn=turn,
        node=node,
        occurrence=occurrence,
        overrides=overrides,
        callbacks=[*extra_callbacks],
        metadata={
            "conversation_id": thread_id,
            "assistant": "ai-geographic",
            "source": "debug-replay",
        },
        tags=[],
    )
