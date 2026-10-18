from ai_lib.llm import provider_order

from src.core.llm.keys import key_client
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq
from src.core.llm.llm_openai import llm_openai

BUILDERS = {"gemini": llm_gemini, "groq": llm_groq, "openai": llm_openai}
DEFAULT_ORDER = ("gemini", "groq")


def llm_chain(temperature=0.7):
    """Provedores na ordem de LLM_PROVIDER_ORDER (só os que têm chave), com fallback entre eles."""
    key_client()
    order = provider_order() or list(DEFAULT_ORDER)
    models = [BUILDERS[provider](temperature=temperature) for provider in order]
    return models[0].with_fallbacks(models[1:]) if len(models) > 1 else models[0]
