from fastapi import APIRouter, Header, HTTPException

from src.api.schemas.chat import ChatRequest, ChatResponse
from src.workflow.runner import execute_turn

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def conversar(
    requisicao: ChatRequest, authorization: str | None = Header(None)
) -> ChatResponse:
    """Recebe uma mensagem do usuário e devolve a resposta do assistente."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Authorization header deve ser 'Bearer <token>'"
        )
    user_token = authorization.removeprefix("Bearer ")

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
        specialists_used=metadata.get("specialists_used", []),
        workflow_steps=metadata.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
    )
