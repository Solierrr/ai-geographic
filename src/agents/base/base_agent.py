from langchain.agents import create_agent

from src.agents.base.base_prompt import build_system_prompt
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq


def get_default_llm():
    """Retorna o Gemini como modelo principal, com Groq como fallback."""
    return llm_gemini().with_fallbacks([llm_groq()])


def build_agent(
    specific_prompt: str,
    tools: list | None = None,
    user_type: str | None = None,
    user_details: dict | None = None,
    include_date: bool = True,
    include_communication_standards: bool = True,
):
    """Constrói um agente com o system prompt padronizado."""
    prompt = build_system_prompt(
        specific_prompt=specific_prompt,
        include_communication_standards=include_communication_standards,
        user_type=user_type,
        user_details=user_details,
        include_date=include_date,
    )
    return create_agent(
        model=get_default_llm(),
        tools=tools or [],
        system_prompt=prompt,
    )
