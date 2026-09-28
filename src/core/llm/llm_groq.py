from langchain_groq import ChatGroq

from src.core.config.settings import settings


def llm_groq(model="openai/gpt-oss-120b", temperature=0.7):
    return ChatGroq(
        model=model,
        temperature=temperature,
        api_key=settings.GROQ_API_KEY,
    )
