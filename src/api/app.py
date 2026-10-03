from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import chat
from src.core.config.settings import settings
from src.infra.database.mongo.indexes.user_memory_indexes import (
    ensure_user_memory_indexes,
)
from src.infra.external.google_registry import (
    close_google_registry_client,
    get_google_registry_client,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_user_memory_indexes()
    get_google_registry_client()
    try:
        yield
    finally:
        await close_google_registry_client()


app = FastAPI(
    title="ai-geographic API",
    description="Assistente geográfico para endereços, fusos, potencial solar e deslocamentos.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(chat.router)


@app.get("/health")
def health() -> dict:
    """Responde 'ok' se o servidor subiu, listando configuração ausente."""
    missing = []
    if not settings.GOOGLE_REGISTRY_URL:
        missing.append("GOOGLE_REGISTRY_URL")
    if not settings.REGISTRY_CONSUMER_TOKEN:
        missing.append("REGISTRY_CONSUMER_TOKEN")
    if not settings.GOOGLE_MAPS_API_KEY:
        missing.append("GOOGLE_MAPS_API_KEY")

    return {
        "status": "ok" if not missing else "atencao",
        "missing_settings": missing,
    }
