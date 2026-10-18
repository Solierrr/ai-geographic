import os

from ai_lib.llm import get_chat_model

from src.core.llm.keys import key_client


def llm_gemini(model=None, temperature=0.7):
    model = model or os.getenv("LLM_MODEL_GEMINI") or "gemini-2.5-flash"
    return get_chat_model(
        "gemini", model=model, temperature=temperature, client=key_client()
    )
