"""Integrações locais temporárias de Routes e Weather do Google."""

import math
from datetime import datetime, timedelta, timezone

import httpx

from src.core.config.settings import settings
from src.core.travel.models import (
    Coordinate,
    RouteOption,
    WeatherEvidence,
)


class GeographicProviderError(Exception):
    def __init__(self, kind: str):
        self.kind = kind
        super().__init__(kind)


def _ensure_key() -> str:
    if not settings.GOOGLE_MAPS_API_KEY:
        raise GeographicProviderError("unavailable")
    return settings.GOOGLE_MAPS_API_KEY


async def _request(method: str, url: str, **kwargs) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(method, url, **kwargs)
        if response.status_code == 429:
            raise GeographicProviderError("quota")
        if response.status_code == 404:
            raise GeographicProviderError("not_found")
        if response.status_code >= 500:
            raise GeographicProviderError("unavailable")
        if response.status_code >= 400:
            raise GeographicProviderError("invalid_request")
        payload = response.json()
        if not isinstance(payload, dict):
            raise GeographicProviderError("invalid_response")
        return payload
    except httpx.TimeoutException as exc:
        raise GeographicProviderError("timeout") from exc
    except httpx.TransportError as exc:
        raise GeographicProviderError("unavailable") from exc
    except ValueError as exc:
        raise GeographicProviderError("invalid_response") from exc


async def compute_routes(
    origin: Coordinate,
    destination: Coordinate,
    mode: str,
    departure_at: datetime,
    modifiers: dict[str, bool] | None = None,
) -> list[RouteOption]:
    if mode not in {"DRIVE", "WALK"}:
        raise GeographicProviderError("unsupported")
    request: dict = {
        "origin": {"location": {"latLng": origin.model_dump()}},
        "destination": {"location": {"latLng": destination.model_dump()}},
        "travelMode": mode,
        "computeAlternativeRoutes": True,
        "languageCode": "pt-BR",
    }
    if mode == "DRIVE":
        request["routingPreference"] = "TRAFFIC_AWARE"
        request["departureTime"] = departure_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if modifiers:
            request["routeModifiers"] = {
                key: value for key, value in modifiers.items()
                if key in {"avoidTolls", "avoidHighways"} and value
            }
    payload = await _request(
        "POST",
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        headers={
            "X-Goog-Api-Key": _ensure_key(),
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
        },
        json=request,
    )
    result = []
    for index, item in enumerate(payload.get("routes", [])[:3]):
        try:
            duration = int(float(item["duration"].removesuffix("s")))
            distance = int(item["distanceMeters"])
            result.append(
                RouteOption(
                    route_id=f"route-{index + 1}",
                    duration_seconds=duration,
                    distance_meters=distance,
                    departure_at=departure_at,
                    arrival_at=departure_at + timedelta(seconds=duration),
                    encoded_polyline=item.get("polyline", {}).get("encodedPolyline"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return result


async def hourly_weather(coordinate: Coordinate, at: datetime, role: str) -> WeatherEvidence | None:
    now = datetime.now(timezone.utc)
    at = at.astimezone(timezone.utc)
    if at < now - timedelta(hours=1) or at > now + timedelta(hours=239):
        return None
    hours = min(240, max(2, math.ceil((at - now).total_seconds() / 3600) + 2))
    params: dict = {
        "location.latitude": coordinate.latitude,
        "location.longitude": coordinate.longitude,
        "hours": hours,
        "pageSize": 24,
        "key": _ensure_key(),
    }
    for _ in range(10):
        payload = await _request(
            "GET", "https://weather.googleapis.com/v1/forecast/hours:lookup", params=params
        )
        for item in payload.get("forecastHours", []):
            try:
                start = datetime.fromisoformat(item["interval"]["startTime"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(item["interval"]["endTime"].replace("Z", "+00:00"))
                if start <= at < end:
                    probability = item.get("precipitation", {}).get("probability", {}).get("percent")
                    return WeatherEvidence(
                        role=role,
                        route_id="",
                        at=at,
                        interval_start=start,
                        interval_end=end,
                        precipitation_probability=probability,
                        condition=item.get("weatherCondition", {}).get("description", {}).get("text"),
                        fetched_at=datetime.now(timezone.utc),
                    )
            except (KeyError, TypeError, ValueError):
                continue
        token = payload.get("nextPageToken")
        if not token:
            return None
        params["pageToken"] = token
    return None
