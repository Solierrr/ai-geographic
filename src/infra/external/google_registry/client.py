"""Cliente HTTP assíncrono e reutilizável do google-registry."""

import asyncio
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from src.core.config.settings import settings
from src.infra.external.google_registry.errors import (
    GoogleRegistryError,
    RegistryAuthenticationError,
    RegistryInvalidRequestError,
    RegistryInvalidResponseError,
    RegistryNotFoundError,
    RegistryQuotaExceededError,
    RegistryTimeoutError,
    RegistryUnavailableError,
)

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)

_AUTH_CODES = {"GoogleAuthenticationException", "GoogleAuthorizationException"}
_QUOTA_CODES = {"GoogleRateLimitException"}
_TIMEOUT_CODES = {"GoogleTimeoutException"}
_UNAVAILABLE_CODES = {"GoogleUnavailableException"}
_INVALID_CODES = {"GoogleValidationException", "RequestValidationError"}


class GoogleRegistryClient:
    """Isola transporte, códigos HTTP e parsing dos DTOs do registry."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout),
        )

    async def request_model(
        self,
        method: str,
        path: str,
        response_model: type[ResponseModel],
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> ResponseModel:
        try:
            response = await self._http.request(method, path, params=params, json=json)
        except httpx.TimeoutException as exc:
            raise RegistryTimeoutError("google-registry excedeu o tempo limite") from exc
        except httpx.TransportError as exc:
            raise RegistryUnavailableError("google-registry indisponível") from exc

        if response.status_code >= 400:
            raise _error_for_response(response)
        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise TypeError("payload não é um objeto")
            return response_model.model_validate(payload)
        except (ValueError, TypeError, ValidationError) as exc:
            raise RegistryInvalidResponseError("resposta inválida do google-registry") from exc

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()


def _error_for_response(response: httpx.Response) -> GoogleRegistryError:
    code = None
    try:
        body = response.json()
        if isinstance(body, dict) and isinstance(body.get("code"), str):
            code = body["code"]
    except ValueError:
        pass

    status = response.status_code
    if status in {400, 422} or code in _INVALID_CODES:
        return RegistryInvalidRequestError("requisição rejeitada pelo google-registry")
    if status == 404:
        return RegistryNotFoundError("recurso não encontrado no google-registry")
    if code in _AUTH_CODES:
        return RegistryAuthenticationError("falha de autenticação ou configuração do provider")
    if code in _QUOTA_CODES:
        return RegistryQuotaExceededError("quota do provider excedida")
    if status == 504 or code in _TIMEOUT_CODES:
        return RegistryTimeoutError("google-registry excedeu o tempo limite")
    if status == 503 or code in _UNAVAILABLE_CODES:
        return RegistryUnavailableError("google-registry temporariamente indisponível")
    if status == 502:
        return RegistryInvalidResponseError("falha de autenticação ou resposta inválida do provider")
    return RegistryUnavailableError("falha inesperada no google-registry")


_client: GoogleRegistryClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def get_google_registry_client() -> GoogleRegistryClient:
    """Retorna um cliente por event loop, reutilizando o pool de conexões."""
    global _client, _client_loop

    loop = asyncio.get_running_loop()
    if _client is None or _client_loop is not loop:
        _client = GoogleRegistryClient(
            base_url=settings.GOOGLE_REGISTRY_URL,
            timeout=settings.GOOGLE_REGISTRY_TIMEOUT_SECONDS,
        )
        _client_loop = loop
    return _client


async def close_google_registry_client() -> None:
    global _client, _client_loop
    if _client is not None:
        await _client.aclose()
    _client = None
    _client_loop = None
