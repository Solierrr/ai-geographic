import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    title="ai-geographic API",
    description="Assistente para localizar destinos e recomendar deslocamentos com dados de rota e clima.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:5174,http://127.0.0.1:5174,https://web-sandbox-7ug0.onrender.com").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(chat.router)


@app.get("/health")
def health() -> dict:
    """Responde 'ok' se o servidor subiu, listando configuração ausente."""
    missing = []
    if not settings.REGISTRY_URL:
        missing.append("REGISTRY_URL")
    if not settings.REGISTRY_CONSUMER_TOKEN:
        missing.append("REGISTRY_CONSUMER_TOKEN")
    if not settings.GOOGLE_MAPS_API_KEY:
        missing.append("GOOGLE_MAPS_API_KEY")

    return {
        "status": "ok" if not missing else "atencao",
        "missing_settings": missing,
    }
