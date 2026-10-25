import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.infra.database.mongo.async_client import get_async_mongodb_client
from src.version import VERSION

router = APIRouter(tags=["Saúde"])

_READY_TIMEOUT_SECONDS = 2


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["UP"])
    version: str = Field(..., examples=["0.1.1"])


class ReadyResponse(BaseModel):
    status: str = Field(..., examples=["UP"])


async def _ping_mongo() -> None:
    await get_async_mongodb_client()["assessor_inteligente"].command("ping")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Indica se o processo está vivo",
    description="Só o processo, sem consultar dependências; traz a versão do release.",
    operation_id="getHealth",
    openapi_extra={"security": []},
)
async def health() -> HealthResponse:
    return HealthResponse(status="UP", version=VERSION)


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Indica se o serviço está pronto para atender",
    description=(
        'Confere o Mongo (checkpointer e memória) e responde 503 com {"status": "DOWN"} '
        "quando ele não responde. Os provedores de LLM ficam de fora porque há "
        "fallback entre eles."
    ),
    operation_id="getReady",
    openapi_extra={"security": []},
)
async def ready() -> JSONResponse:
    try:
        await asyncio.wait_for(_ping_mongo(), timeout=_READY_TIMEOUT_SECONDS)
    except Exception:  # noqa: BLE001
        return JSONResponse({"status": "DOWN"}, status_code=503)
    return JSONResponse({"status": "UP"})
