"""Modo debug do agente de campo: roda um turno e devolve o que cada nó do grafo
recebeu e devolveu. Só para uso interno: sempre ativo, mas restrito aos admins,
fora do OpenAPI e restrito aos `sub` de `DEBUG_ADMIN_SUBS`. Não grava nada no
api-messenger nem na memória de longo prazo."""

import asyncio
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import Field

from src.api.schemas.chat import ChatRequest, ChatResponse
from src.core.config.settings import settings
from src.core.security.jwt import decode_user_id
from src.workflow.observability.debug_tracker import DebugTracker, mask_pii
from src.workflow.runner import execute_turn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"], include_in_schema=False)
bearer_scheme = HTTPBearer(auto_error=False)

DEBUG_ALLOWED_ENVIRONMENTS = frozenset({"LOCAL", "DEV", "QA", "PROD"})
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


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
    if sub.lower() not in debug_admin_subs():
        raise HTTPException(status_code=403, detail="Sem permissão para o modo debug")
    logger.info(
        "Turno de debug (sub=%s, ambiente=%s)", sub.lower(), settings.ENVIRONMENT
    )
    return credentials.credentials, sub.lower()


@router.post("/chat", response_model=DebugChatResponse)
async def conversar_com_debug(
    requisicao: ChatRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    token, sub = await _authorize(credentials)

    from src.workflow.graph.graph import compiled_app

    collector = DebugTracker()
    # A conversa de debug tem thread própria (por admin), separada das reais.
    thread_id = f"debug:{sub}:{requisicao.conversation_id}"
    try:
        final_state = await execute_turn(
            thread_id,
            requisicao.message,
            compiled_app,
            user_token=token,
            persist=False,
            extra_callbacks=[collector],
        )
    except Exception as error:
        logger.exception("Falha no turno de debug")
        return JSONResponse(
            status_code=500,
            content={
                "detail": mask_pii(f"{type(error).__name__}: {error}"[:1000])[:500],
                "debug": collector.snapshot(),
            },
        )

    final_message = final_state["messages"][-1]
    metadata = final_message.additional_kwargs
    debug = collector.snapshot()
    debug["environment"] = settings.ENVIRONMENT
    debug["persisted"] = False
    return DebugChatResponse(
        response=final_message.content,
        specialists_used=metadata.get("specialists_used", []),
        workflow_steps=metadata.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
        debug=debug,
    )
