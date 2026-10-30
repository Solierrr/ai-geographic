"""Modo debug do agente de campo: roda um turno e devolve o que cada nó do grafo
recebeu e devolveu. Só para uso interno: sempre ativo, mas restrito aos admins,
fora do OpenAPI e restrito aos `sub` de `DEBUG_ADMIN_SUBS`. O turno normal grava
conversa, mensagens e steps no api-messenger (para aparecer em Conversas e
Dashboards), mas não grava na memória de longo prazo; a execução personalizada de
um nó não grava nada."""

import asyncio
import logging
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from src.api.schemas.chat import ChatRequest, ChatResponse
from src.core.config.settings import settings
from src.core.security.jwt import decode_user_id
from src.workflow.debug_replay import ReplayError, count_turns
from src.workflow.observability.debug_tracker import DebugTracker, mask_pii
from src.workflow.outcome import Outcome
from src.workflow.runner import execute_single_node, execute_turn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"], include_in_schema=False)
bearer_scheme = HTTPBearer(auto_error=False)

DEBUG_ALLOWED_ENVIRONMENTS = frozenset({"LOCAL", "DEV", "QA", "PROD"})
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


class PromptMessage(BaseModel):
    type: str = Field(max_length=32)
    content: str


class PromptOverrideItem(BaseModel):
    call: int = Field(ge=0, le=50)
    prompt: list[PromptMessage]


class CustomRun(BaseModel):
    turn: int = Field(
        0, ge=0, le=1000, description="Posição do turno na conversa de debug."
    )
    node: str = Field(pattern=r"^[a-z0-9_]{1,64}$")
    occurrence: int = Field(0, ge=0, le=50, description="Qual execução do nó no turno.")
    stop_after_node: Literal[True] = True
    prompts: list[PromptOverrideItem] = Field(default_factory=list, max_length=50)

    @field_validator("prompts")
    @classmethod
    def _calls_unicas(cls, items):
        if len({item.call for item in items}) != len(items):
            raise ValueError("Chamada de LLM repetida em prompts")
        return items


class DebugChatRequest(ChatRequest):
    custom: CustomRun | None = None


class DebugChatResponse(ChatResponse):
    debug: dict = Field(default_factory=dict)


def debug_admin_subs() -> set[str]:
    subs = {part.strip().lower() for part in settings.DEBUG_ADMIN_SUBS.split(",")}
    return {sub for sub in subs if _UUID.match(sub)}


def debug_enabled() -> bool:
    """A rota só existe em ambiente permitido e com ao menos um admin configurado."""
    return settings.ENVIRONMENT.strip().upper() in DEBUG_ALLOWED_ENVIRONMENTS and bool(
        debug_admin_subs()
    )


async def _last_turn(workflow, thread_id: str) -> int | None:
    try:
        return await count_turns(workflow, thread_id) - 1
    except Exception:
        logger.warning(
            "Não foi possível contar os turnos de %s", thread_id, exc_info=True
        )
        return None


async def _authorize(
    credentials: HTTPAuthorizationCredentials | None,
) -> tuple[str, str]:
    """Devolve (token, sub) de um admin; falha fechado em qualquer dúvida."""
    if not debug_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    if credentials is None:
        raise HTTPException(
            status_code=401, detail="Authorization header deve ser 'Bearer <token>'"
        )
    sub = await asyncio.to_thread(decode_user_id, credentials.credentials)
    if not sub:
        raise HTTPException(status_code=401, detail="Token inválido")
    admin = next((item for item in debug_admin_subs() if item == sub.lower()), None)
    if admin is None:
        raise HTTPException(status_code=403, detail="Sem permissão para o modo debug")
    logger.info("Turno de debug (sub=%s, ambiente=%s)", admin, settings.ENVIRONMENT)
    return credentials.credentials, admin


@router.post("/chat", response_model=DebugChatResponse)
async def conversar_com_debug(
    requisicao: DebugChatRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    token, sub = await _authorize(credentials)

    from src.workflow.graph.graph import compiled_app

    collector = DebugTracker()
    thread_id = f"debug:{sub}:{requisicao.conversation_id}"
    if requisicao.custom is not None:
        return await _executar_no(
            requisicao, compiled_app, token, thread_id, collector, sub
        )
    try:
        final_state = await execute_turn(
            thread_id,
            requisicao.message,
            compiled_app,
            user_token=token,
            persist=False,
            save_history=True,
            extra_callbacks=[collector],
        )
    except Exception as error:
        logger.exception("Falha no turno de debug")
        return JSONResponse(
            status_code=500,
            content={
                "detail": mask_pii(f"{type(error).__name__}: {error}"[:1000])[:500],
                "debug": {
                    **collector.snapshot(),
                    "turn": await _last_turn(compiled_app, thread_id),
                },
            },
        )

    final_message = final_state["messages"][-1]
    metadata = final_message.additional_kwargs
    debug = collector.snapshot()
    debug["environment"] = settings.ENVIRONMENT
    debug["persisted"] = True
    debug["turn"] = await _last_turn(compiled_app, thread_id)
    return DebugChatResponse(
        response=final_message.content,
        outcome=final_state.get("outcome", Outcome.ANSWERED),
        reason=final_state.get("reason"),
        specialists_used=metadata.get("specialists_used", []),
        workflow_steps=metadata.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
        debug=debug,
    )


def _no_para_log(workflow, node: str) -> str:
    return next(
        (nome for nome in getattr(workflow, "nodes", ()) if nome == node),
        "desconhecido",
    )


async def _executar_no(requisicao, workflow, token, thread_id, collector, sub):
    custom = requisicao.custom
    no_log = _no_para_log(workflow, custom.node)
    logger.info(
        "Execução personalizada de nó (sub=%s, nó=%s, turno=%s, prompts=%s)",
        sub,
        no_log,
        custom.turn,
        len(custom.prompts),
    )
    overrides: dict[int, dict[int, str]] = {}
    for item in custom.prompts:
        overrides[item.call] = {
            position: message.content
            for position, message in enumerate(item.prompt)
            if message.type == "system"
        }
    try:
        _, proximos, aplicados = await execute_single_node(
            thread_id,
            workflow,
            token,
            turn=custom.turn,
            node=custom.node,
            occurrence=custom.occurrence,
            overrides=overrides,
            extra_callbacks=[collector],
        )
    except ReplayError as error:
        return JSONResponse(status_code=error.status, content={"detail": error.detail})
    except Exception as error:
        logger.exception("Falha na execução personalizada do nó %s", no_log)
        return JSONResponse(
            status_code=500,
            content={
                "detail": mask_pii(f"{type(error).__name__}: {error}"[:1000])[:500],
                "debug": collector.snapshot(),
            },
        )
    debug = collector.snapshot()
    debug["environment"] = settings.ENVIRONMENT
    debug["persisted"] = False
    debug["custom"] = {
        "node": custom.node,
        "turn": custom.turn,
        "occurrence": custom.occurrence,
        "stopped": True,
        "overrides_applied": aplicados,
        "next": list(proximos),
    }
    return DebugChatResponse(response="", outcome=Outcome.ANSWERED, debug=debug)
