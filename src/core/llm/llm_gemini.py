from ai_lib.llm import get_chat_model

from src.core.llm.registry import registry_client


def llm_gemini(model="gemini-2.5-flash", temperature=0.7):
    return get_chat_model(
        "gemini", model=model, temperature=temperature, client=registry_client()
    )
