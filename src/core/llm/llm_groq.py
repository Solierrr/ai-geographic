import os

from ai_lib.llm import get_chat_model

from src.core.llm.keys import key_client


def llm_groq(model=None, temperature=0.7):
    model = model or os.getenv("LLM_MODEL_GROQ") or "openai/gpt-oss-120b"
    return get_chat_model("groq", model=model, temperature=temperature, client=key_client())
