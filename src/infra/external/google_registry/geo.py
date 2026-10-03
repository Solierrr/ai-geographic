"""Contrato interno de fuso horário sobre a collection geo do registry."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ValidationError

from src.core.travel.models import Coordinate
from src.infra.external.google_registry.client import (
    GoogleRegistryClient,
    get_google_registry_client,
)
from src.infra.external.google_registry.errors import (
    RegistryInvalidRequestError,
    RegistryInvalidResponseError,
)
from src.infra.external.google_registry.models import TimezoneResponse


@dataclass(frozen=True)
class TimezoneInfo:
    zone: ZoneInfo
    utc_offset_seconds: int


class GeoProvider:
    def __init__(self, client: GoogleRegistryClient | None = None) -> None:
        self._client = client

    async def timezone(
        self,
        coordinate: Coordinate,
        at: datetime | None = None,
    ) -> TimezoneInfo:
        try:
            location = Coordinate.model_validate(coordinate)
        except ValidationError as exc:
            raise RegistryInvalidRequestError("coordenadas inválidas para geo") from exc
        params: dict[str, object] = {
            "latitude": location.latitude,
            "longitude": location.longitude,
        }
        if at is not None:
            params["at"] = at.isoformat()
        response = await (self._client or get_google_registry_client()).request_model(
            "GET", "/v1/geo/timezone", TimezoneResponse, params=params
        )
        try:
            zone = ZoneInfo(response.timezone_id)
        except ZoneInfoNotFoundError as exc:
            raise RegistryInvalidResponseError("timezone IANA inválido no registry") from exc
        return TimezoneInfo(zone=zone, utc_offset_seconds=response.utc_offset_seconds)


async def timezone_for(coordinate: Coordinate, at: datetime) -> ZoneInfo:
    return (await GeoProvider().timezone(coordinate, at)).zone


async def get_timezone(
    coordinate: Coordinate, at: datetime | None = None
) -> TimezoneInfo:
    return await GeoProvider().timezone(coordinate, at)
