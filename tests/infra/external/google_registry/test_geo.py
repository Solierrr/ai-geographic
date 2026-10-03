from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

from src.core.travel.models import Coordinate
from src.infra.external.google_registry.client import GoogleRegistryClient
from src.infra.external.google_registry.errors import (
    RegistryInvalidRequestError,
    RegistryNotFoundError,
)
from src.infra.external.google_registry.geo import GeoProvider


def _provider(handler):
    http = httpx.AsyncClient(base_url="http://registry", transport=httpx.MockTransport(handler))
    client = GoogleRegistryClient(base_url="http://registry", timeout=2, http_client=http)
    return GeoProvider(client), http


async def test_timezone_is_converted_to_zoneinfo_and_serializes_at():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"timezone_id": "America/Manaus", "utc_offset_seconds": -14400},
        )

    provider, http = _provider(handler)
    result = await provider.timezone(
        Coordinate(latitude=-3.1, longitude=-60),
        datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    assert isinstance(result.zone, ZoneInfo)
    assert str(result.zone) == "America/Manaus"
    assert requests[0].url.params["at"].startswith("2026-07-01")
    await http.aclose()


async def test_invalid_coordinate_is_rejected_before_http():
    provider, http = _provider(lambda _request: pytest.fail("HTTP não deveria ser chamado"))
    with pytest.raises(RegistryInvalidRequestError):
        await provider.timezone({"latitude": 91, "longitude": 0})
    await http.aclose()


async def test_timezone_not_found_is_not_empty_success():
    provider, http = _provider(lambda _request: httpx.Response(404, json={"code": "x"}))
    with pytest.raises(RegistryNotFoundError):
        await provider.timezone(Coordinate(latitude=0, longitude=0))
    await http.aclose()
