import asyncio
from uuid import uuid4

from src.core.config.settings import settings
from src.workflow.runner import execute_turn


async def run_chat():
    from src.workflow.graph.graph import compiled_app

    if not settings.TEST_USER_TOKEN:
        print(
            "Defina TEST_USER_TOKEN no .env com um JWT válido (mock-idp ou "
            "api-auth) antes de rodar."
        )
        return

    conversation_id = str(uuid4())

    while True:
        try:
            user_input = input("\n\033[94m> ")
            print("\033[0m", end="")
            if user_input.lower() in ("sair", "fim", "quit"):
                fim = "Encerrando"
                for c in range(4):
                    print(fim + "." * c)
                    if c != 3:
                        await asyncio.sleep(1)
                break

            final_state = await execute_turn(
                conversation_id,
                user_input,
                compiled_app,
                user_token=settings.TEST_USER_TOKEN,
            )
            print(f"{final_state['messages'][-1].content}")

        except (ConnectionError, TimeoutError, ValueError, RuntimeError) as error:
            print(f"Ocorreu um erro: {error}")


if __name__ == "__main__":
    asyncio.run(run_chat())
