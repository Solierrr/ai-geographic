from ai_lib.llm import get_chat_model

from src.core.llm.keys import key_client


def llm_openai(model=None, temperature=0.7):
    # Sem modelo padrão: vem de LLM_MODEL_OPENAI (ex.: gpt-6-luna).
    return get_chat_model("openai", model=model, temperature=temperature, client=key_client())
