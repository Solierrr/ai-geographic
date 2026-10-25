from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.schemas.chat import ChatRequest, ChatResponse
from src.workflow.outcome import Outcome
from src.workflow.runner import execute_turn

router = APIRouter(tags=["Conversa"])
bearer_scheme = HTTPBearer(
    scheme_name="bearerAuth", bearerFormat="JWT", auto_error=False
)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Envia uma mensagem ao copiloto de campo",
    description=(
        "Executa um turno da conversa com o JWT do profissional. Recusa do guardrail, "
        "falha de ferramenta e queda de provedor não são erro HTTP: voltam 200 com "
        "`outcome` e `reason`."
    ),
    operation_id="sendChatMessage",
    responses={
        401: {"description": "JWT ausente ou malformado"},
        422: {"description": "Corpo da requisição inválido"},
    },
    openapi_extra={
        "x-error-codes": ["UNAUTHENTICATED", "VALIDATION_FAILED", "INTERNAL_ERROR"]
    },
)
async def conversar(
    requisicao: ChatRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> ChatResponse:
    if credentials is None:
        raise HTTPException(
            status_code=401, detail="Authorization header deve ser 'Bearer <token>'"
        )
    user_token = credentials.credentials

    from src.workflow.graph.graph import compiled_app

    final_state = await execute_turn(
        requisicao.conversation_id,
        requisicao.message,
        compiled_app,
        user_token=user_token,
    )
    final_message = final_state["messages"][-1]
    metadata = final_message.additional_kwargs

    return ChatResponse(
        response=final_message.content,
        outcome=final_state.get("outcome", Outcome.ANSWERED),
        reason=final_state.get("reason"),
        specialists_used=metadata.get("specialists_used", []),
        workflow_steps=metadata.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
    )
