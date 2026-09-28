from langchain_google_genai import ChatGoogleGenerativeAI

from src.core.config.settings import settings


def llm_gemini(model="gemini-2.5-flash", temperature=0.7):
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        api_key=settings.GOOGLE_API_KEY,
    )
