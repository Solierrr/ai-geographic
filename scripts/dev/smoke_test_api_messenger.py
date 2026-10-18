"""Testa isoladamente a integração com o api-messenger, sem subir o grafo/LLM.

Uso:
    python scripts/dev/testar_api_messenger.py "<jwt-do-usuario>"

Requer API_MESSENGER_URL (e ENVIRONMENT, se quiser algo diferente de LOCAL)
configurados no .env ou no ambiente.
"""

import asyncio
import sys
from pathlib import Path

# sobe de scripts/dev/ até a raiz do projeto, garante que "src" seja achado
# mesmo rodando "python scripts\dev\smoke_test_api_messenger.py" direto
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.config.settings import settings
from src.infra.api_messenger.client import criar_conversa_chatbot, enviar_mensagem_chatbot


async def main(user_token: str) -> None:
    print(f"API_MESSENGER_URL: {settings.API_MESSENGER_URL}")
    print(f"ENVIRONMENT: {settings.ENVIRONMENT}")

    print("\n> Criando conversa (chatbot-conversations, com JWT do usuário)...")
    conversation_id = await criar_conversa_chatbot("lead", {}, user_token=user_token)
    print(f"  conversation_id = {conversation_id}")

    print("\n> Enviando mensagem de teste (internal/messages, com token de serviço)...")
    await enviar_mensagem_chatbot(
        conversation_id,
        "Mensagem de teste do scripts/dev/testar_api_messenger.py",
        metadata={"origem": "script-de-teste"},
    )
    print("  mensagem enviada com sucesso")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python scripts/dev/testar_api_messenger.py \"<jwt-do-usuario>\"")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
