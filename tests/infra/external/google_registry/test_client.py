import httpx
import pytest

from src.infra.external.google_registry import client as client_module
from src.infra.external.google_registry.client import GoogleRegistryClient
from src.infra.external.google_registry.errors import (
    RegistryAuthenticationError,
    RegistryInvalidRequestError,
    RegistryInvalidResponseError,
    RegistryNotFoundError,
    RegistryQuotaExceededError,
    RegistryTimeoutError,
    RegistryUnavailableError,
)
from src.infra.external.google_registry.models import TimezoneResponse


def _client(handler) -> tuple[GoogleRegistryClient, httpx.AsyncClient]:
    http = httpx.AsyncClient(
        base_url="http://google-registry:8000",
        transport=httpx.MockTransport(handler),
    )
    return GoogleRegistryClient(base_url="http://ignored", timeout=2, http_client=http), http


async def test_builds_url_serializes_params_and_parses_response():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"timezone_id": "America/Sao_Paulo", "utc_offset_seconds": -10800},
        )

    client, http = _client(handler)
    result = await client.request_model(
        "GET",
        "/v1/geo/timezone",
        TimezoneResponse,
        params={"latitude": -23.5, "longitude": -46.6},
    )

    assert str(requests[0].url).startswith(
        "http://google-registry:8000/v1/geo/timezone?"
    )
    assert requests[0].url.params["latitude"] == "-23.5"
    assert result.timezone_id == "America/Sao_Paulo"
    await http.aclose()


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (400, {"code": "GoogleValidationException"}, RegistryInvalidRequestError),
        (404, {"code": "GoogleNotFoundException"}, RegistryNotFoundError),
        (422, {"detail": []}, RegistryInvalidRequestError),
        (502, {"code": "GoogleAuthenticationException"}, RegistryAuthenticationError),
        (502, {"code": "GoogleUpstreamException"}, RegistryInvalidResponseError),
        (503, {"code": "GoogleRateLimitException"}, RegistryQuotaExceededError),
        (503, {"code": "GoogleUnavailableException"}, RegistryUnavailableError),
        (504, {"code": "GoogleTimeoutException"}, RegistryTimeoutError),
    ],
)
async def test_translates_registry_errors(status, body, error):
    client, http = _client(lambda _request: httpx.Response(status, json=body))
    with pytest.raises(error):
        await client.request_model("GET", "/v1/test", TimezoneResponse)
    await http.aclose()


@pytest.mark.parametrize(
    ("transport_error", "expected"),
    [
        (httpx.ReadTimeout("slow"), RegistryTimeoutError),
        (httpx.ConnectError("down"), RegistryUnavailableError),
    ],
)
async def test_translates_transport_errors(transport_error, expected):
    def handler(request):
        transport_error.request = request
        raise transport_error

    client, http = _client(handler)
    with pytest.raises(expected):
        await client.request_model("GET", "/v1/test", TimezoneResponse)
    await http.aclose()


async def test_rejects_unexpected_payload():
    client, http = _client(lambda _request: httpx.Response(200, json={"unexpected": True}))
    with pytest.raises(RegistryInvalidResponseError):
        await client.request_model("GET", "/v1/geo/timezone", TimezoneResponse)
    await http.aclose()


async def test_global_client_reuses_connections_and_closes(monkeypatch):
    monkeypatch.setattr(client_module, "_client", None)
    monkeypatch.setattr(client_module, "_client_loop", None)
    monkeypatch.setattr(client_module.settings, "GOOGLE_REGISTRY_URL", "http://registry")

    first = client_module.get_google_registry_client()
    second = client_module.get_google_registry_client()
    assert first is second

    await client_module.close_google_registry_client()
    assert first._http.is_closed
    assert client_module._client is None
