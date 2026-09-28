import asyncio
import logging
from uuid import uuid4

from langchain_core.messages import HumanMessage

from src.core.guardrails.anonymize import anonymize_text
from src.core.security.jwt import decode_user_id
from src.infra.api_messenger.client import (
    criar_conversa_chatbot,
    enviar_mensagem_chatbot,
    enviar_mensagem_usuario,
)
from src.infra.database.mongo.repositories.user_memory_repository import (
    get_user_memory,
    upsert_user_memory,
)
from src.workflow.memory.memory_extraction import extrair_fatos_atualizados
from src.workflow.observability.step_tracker import StepTracker

logger = logging.getLogger(__name__)

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


async def _get_or_create_conversation_id(thread_id: str, user_token: str) -> str:
    """Reaproveita, por thread_id, a conversa já aberta no api-messenger;
    cria uma nova na primeira mensagem do turno."""
    conversation_id = _conversations_por_thread.get(thread_id)
    if conversation_id is None:
        conversation_id = await criar_conversa_chatbot(
            "lead", {}, user_token=user_token
        )
        _conversations_por_thread[thread_id] = conversation_id
    return conversation_id


async def execute_turn(
    conversation_id: str, user_input: str, workflow, user_token: str
) -> dict:
    turn_id = str(uuid4())
    anonymized_user_input, _ = anonymize_text(user_input)
    api_conversation_id = await _get_or_create_conversation_id(
        conversation_id, user_token
    )

    await enviar_mensagem_usuario(
        api_conversation_id, anonymized_user_input, user_token
    )

    tracker = StepTracker(conversation_id=api_conversation_id)

    user_id = await asyncio.to_thread(decode_user_id, user_token)
    fatos_existentes = await get_user_memory(user_id) if user_id else []
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
            "callbacks": [tracker],
        },
    )

    final_message = final_state["messages"][-1]
    anonymized_assistant_response, _ = anonymize_text(final_message.content)
    message_metadata = final_message.additional_kwargs
    audit_metadata = {
        "turnId": turn_id,
        "contentAnonymized": True,
        "specialistsUsed": message_metadata.get("specialists_used", []),
        "workflowSteps": message_metadata.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
    }
    await enviar_mensagem_chatbot(
        api_conversation_id, anonymized_assistant_response, audit_metadata
    )

    if user_id:
        ultima_troca = f"Usuário: {user_input}\nAssistente: {final_message.content}"
        _agendar_atualizacao_memoria(user_id, fatos_existentes, ultima_troca)

    return final_state
