from ai_lib.llm import get_chat_model

from src.core.llm.registry import registry_client


def llm_groq(model="openai/gpt-oss-120b", temperature=0.7):
    return get_chat_model(
        "groq", model=model, temperature=temperature, client=registry_client()
    )
