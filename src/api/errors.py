"""Contrato de erro HTTP: todo 4xx e 5xx sai como application/problem+json."""

import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

from src.core.observability.observability import TRACE_ID_HEADER, mark_error

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"

GENERIC_BY_STATUS = {
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    406: "NOT_ACCEPTABLE",
    409: "CONFLICT",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_FAILED",
    429: "RATE_LIMITED",
    502: "DEPENDENCY_UNAVAILABLE",
    503: "DEPENDENCY_UNAVAILABLE",
}


class ProblemFieldError(BaseModel):
    field: str = Field(..., examples=["message"])
    errorCode: str = Field(..., examples=["VALIDATION_FAILED"])
    detail: str = Field(..., examples=["String should have at least 1 character"])


class ProblemDetail(BaseModel):
    """Corpo de todo erro HTTP do serviço."""

    type: str = Field(..., examples=["about:blank"])
    title: str = Field(..., examples=["UNAUTHENTICATED"])
    status: int = Field(..., examples=[401])
    errorCode: str = Field(..., examples=["UNAUTHENTICATED"])
    detail: str = Field(
        ..., examples=["Authorization header deve ser 'Bearer <token>'"]
    )
    instance: str = Field(..., examples=["/chat"])
    timestamp: datetime
    traceId: str | None = Field(None, examples=["4bf92f3577b34da6a3ce929d0e0e4736"])
    errors: list[ProblemFieldError] | None = None


class ApiError(Exception):
    def __init__(self, status: int, error_code: str, detail: str, **extra):
        self.status = status
        self.error_code = error_code
        self.detail = detail
        self.extra = extra


def _trace_id() -> dict:
    span = trace.get_current_span().get_span_context()
    return {"traceId": format(span.trace_id, "032x")} if span.is_valid else {}


def problem(
    request: Request, status: int, error_code: str, detail: str, **extra
) -> JSONResponse:
    body = {
        "type": "about:blank",
        "title": error_code,
        "status": status,
        "errorCode": error_code,
        "detail": detail,
        "instance": request.url.path,
        "timestamp": datetime.now(UTC).isoformat(),
        **_trace_id(),
        **extra,
    }
    response = JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)
    # o 500 sai pelo ServerErrorMiddleware, fora do middleware de X-Trace-Id -> header posto aqui também
    if "traceId" in body:
        response.headers[TRACE_ID_HEADER] = body["traceId"]
    return response


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        mark_error(exc)
        return problem(request, exc.status, exc.error_code, exc.detail, **exc.extra)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        mark_error(exc)
        code = GENERIC_BY_STATUS.get(exc.status_code, "INTERNAL_ERROR")
        response = problem(request, exc.status_code, code, str(exc.detail))
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        mark_error(exc)
        errors = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]),
                "errorCode": "VALIDATION_FAILED",
                "detail": error["msg"],
            }
            for error in exc.errors()
        ]
        return problem(
            request,
            422,
            "VALIDATION_FAILED",
            "Erro de validação nos campos da requisição.",
            errors=errors,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        mark_error(exc)
        logger.exception("Erro inesperado em %s", request.url.path)
        return problem(
            request, 500, "INTERNAL_ERROR", "Ocorreu um erro interno inesperado."
        )
