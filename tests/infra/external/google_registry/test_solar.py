import httpx
import pytest

from src.core.travel.models import Coordinate
from src.infra.external.google_registry.client import GoogleRegistryClient
from src.infra.external.google_registry.errors import (
    RegistryUnavailableError,
    SolarCoverageUnavailableError,
)
from src.infra.external.google_registry.solar import SolarProvider

FULL_PAYLOAD = {
    "imagery_date": "2024-03-05",
    "usable_roof_area_m2": 42.5,
    "max_panel_count": 20,
    "annual_sunshine_hours": 1800.0,
    "carbon_offset_factor_kg_mwh": 400.0,
    "roof_segments": [
        {"pitch_degrees": 20, "azimuth_degrees": 180, "area_m2": 42.5}
    ],
    "panel_capacity_watts": 400,
    "panel_width_meters": 1.1,
    "panel_height_meters": 1.8,
    "panel_configs": [{"panels_count": 10, "yearly_energy_dc_kwh": 6200}],
}


def _provider(response):
    http = httpx.AsyncClient(
        base_url="http://registry",
        transport=httpx.MockTransport(lambda _request: response),
    )
    client = GoogleRegistryClient(base_url="http://registry", timeout=2, http_client=http)
    return SolarProvider(client), http


async def test_roof_viability_with_full_payload():
    provider, http = _provider(httpx.Response(200, json=FULL_PAYLOAD))
    result = await provider.roof_viability(Coordinate(latitude=-23.5, longitude=-46.6))
    assert result.max_panel_count == 20
    assert result.panel_configs[0].yearly_energy_dc_kwh == 6200
    await http.aclose()


async def test_optional_fields_may_be_absent():
    payload = {key: value for key, value in FULL_PAYLOAD.items() if not key.startswith("panel_")}
    provider, http = _provider(httpx.Response(200, json=payload))
    result = await provider.roof_viability(Coordinate(latitude=-23.5, longitude=-46.6))
    assert result.panel_capacity_watts is None
    assert result.panel_configs == []
    await http.aclose()


async def test_absence_of_coverage_is_distinct_from_temporary_failure():
    provider, http = _provider(httpx.Response(404, json={"code": "GoogleNotFoundException"}))
    with pytest.raises(SolarCoverageUnavailableError):
        await provider.roof_viability(Coordinate(latitude=-23.5, longitude=-46.6))
    await http.aclose()

    provider, http = _provider(httpx.Response(503, json={"code": "GoogleUnavailableException"}))
    with pytest.raises(RegistryUnavailableError):
        await provider.roof_viability(Coordinate(latitude=-23.5, longitude=-46.6))
    await http.aclose()
