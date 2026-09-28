from src.infra.api_messenger.client import (
    enviar_mensagem_chatbot,
    enviar_mensagem_usuario,
)


def get_recent_history(state: dict, limit: int = 10) -> list:
    """Retorna as últimas `limit` mensagens já mantidas em memória pelo
    checkpointer do LangGraph (não consulta o banco)."""
    messages = state.get("messages", [])
    return messages[-limit:]


async def log_user_interaction(
    conversation_id: str, content: str, user_token: str
) -> None:
    """Registra uma mensagem do usuário com as permissões desse usuário."""
    await enviar_mensagem_usuario(conversation_id, content, user_token)


async def log_assistant_interaction(
    conversation_id: str, content: str, metadata: dict | None = None
) -> None:
    """Registra a resposta do assistente via autenticação de serviço."""
    await enviar_mensagem_chatbot(conversation_id, content, metadata)
