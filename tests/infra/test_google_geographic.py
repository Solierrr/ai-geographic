import json
from datetime import datetime, timedelta, timezone

import pytest
import respx
from httpx import Response

from src.core.config.settings import settings
from src.core.travel.models import Coordinate
from src.infra.external.google_geographic import (
    compute_routes,
    hourly_weather,
)


@pytest.mark.asyncio
@respx.mock
async def test_routes_are_still_parsed_directly_from_google(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_MAPS_API_KEY", "test-key")
    origin = Coordinate(latitude=-23.5, longitude=-46.6)
    respx.post("https://routes.googleapis.com/directions/v2:computeRoutes").mock(
        return_value=Response(200, json={"routes": [{
            "duration": "900s", "distanceMeters": 5000,
            "polyline": {"encodedPolyline": "abc"},
        }]})
    )
    at = datetime.now(timezone.utc) + timedelta(hours=1)
    routes = await compute_routes(origin, Coordinate(latitude=-23.6, longitude=-46.7), "DRIVE", at)
    assert routes[0].duration_seconds == 900
    assert routes[0].arrival_at == at + timedelta(minutes=15)

    await compute_routes(
        origin,
        Coordinate(latitude=-23.6, longitude=-46.7),
        "DRIVE", at, modifiers={"avoidTolls": True},
    )
    route_request = respx.calls[-1].request
    assert json.loads(route_request.content)["routeModifiers"] == {"avoidTolls": True}


@pytest.mark.asyncio
@respx.mock
async def test_weather_follows_page_token_to_target_hour(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_MAPS_API_KEY", "test-key")
    now = datetime.now(timezone.utc)
    target = now + timedelta(hours=3)
    start = target.replace(minute=0, second=0, microsecond=0)
    route = respx.get("https://weather.googleapis.com/v1/forecast/hours:lookup")
    route.side_effect = [
        Response(200, json={"forecastHours": [], "nextPageToken": "next"}),
        Response(200, json={"forecastHours": [{
            "interval": {
                "startTime": start.isoformat().replace("+00:00", "Z"),
                "endTime": (start + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            },
            "precipitation": {"probability": {"percent": 65}},
        }]}),
    ]
    result = await hourly_weather(Coordinate(latitude=-23.5, longitude=-46.6), target, "origin")
    assert result is not None
    assert result.precipitation_probability == 65
    assert route.call_count == 2
