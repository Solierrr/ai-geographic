import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.api.errors import PROBLEM_JSON, ProblemDetail, register_error_handlers
from src.api.routes import chat, health
from src.core.config.settings import settings
from src.infra.database.mongo.indexes.user_memory_indexes import (
    ensure_user_memory_indexes,
)
from src.version import VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_user_memory_indexes()
    yield


app = FastAPI(
    title="Solaria — ai-geographic",
    description=(
        "Copiloto de campo do profissional de energia solar: planeja a rota até o "
        "cliente, avalia clima e luz do dia de uma região em uma data e estima o "
        "potencial solar do local. Autentique com o JWT do api-auth."
    ),
    version=VERSION,
    contact={"name": "Solaria", "url": "https://github.com/Solierrr"},
    license_info={
        "name": "CC0-1.0",
        "url": "https://creativecommons.org/publicdomain/zero/1.0/",
    },
    servers=[
        {"url": "https://ai-geographic.onrender.com", "description": "QA"},
        {"url": "http://localhost:8000", "description": "Local"},
    ],
    openapi_tags=[
        {"name": "Conversa", "description": "Turnos de conversa com o copiloto."},
        {"name": "Saúde", "description": "Vivo e pronto do serviço."},
    ],
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
    redoc_url=None,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
    },
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:5174,http://127.0.0.1:5174,https://web-sandbox-7ug0.onrender.com").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

register_error_handlers(app)

app.include_router(chat.router)
app.include_router(health.router)


def _problem_detail_responses(schema: dict) -> None:
    schemas = schema.setdefault("components", {}).setdefault("schemas", {})
    schemas.pop("HTTPValidationError", None)
    schemas.pop("ValidationError", None)
    problem = {
        PROBLEM_JSON: {"schema": {"$ref": "#/components/schemas/ProblemDetail"}}
    }
    for path in schema["paths"].values():
        for operation in path.values():
            responses = operation["responses"]
            responses.setdefault("500", {"description": "Erro interno inesperado"})
            for code, response in responses.items():
                if code.startswith(("4", "5")):
                    response["content"] = problem
    problem_schema = ProblemDetail.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    schemas.update(problem_schema.pop("$defs", {}))
    schemas["ProblemDetail"] = problem_schema


def build_openapi(include_internal: bool) -> dict:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers,
        contact=app.contact,
        license_info=app.license_info,
    )
    if not include_internal:
        schema["paths"] = {
            path: item
            for path, item in schema["paths"].items()
            if not path.startswith("/internal/")
        }
    schema["security"] = [{"bearerAuth": []}]
    _problem_detail_responses(schema)
    return schema


def public_openapi() -> dict:
    if app.openapi_schema is None:
        app.openapi_schema = build_openapi(include_internal=False)
    return app.openapi_schema


app.openapi = public_openapi
