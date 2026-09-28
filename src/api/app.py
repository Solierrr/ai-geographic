from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import chat
from src.core.config.settings import settings
from src.infra.database.mongo.indexes.user_memory_indexes import (
    ensure_user_memory_indexes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_user_memory_indexes()
    yield


app = FastAPI(
    title="[NOME_DO_PROJETO] API",
    description="[preencha: descrição curta do assistente de IA e do domínio que ele atende]",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(chat.router)


@app.get("/health")
def health() -> dict:
    """Responde 'ok' se o servidor subiu, listando configuração ausente."""
    missing = []
    if not settings.GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if not settings.GROQ_API_KEY:
        missing.append("GROQ_API_KEY")

    return {
        "status": "ok" if not missing else "atencao",
        "missing_settings": missing,
    }
