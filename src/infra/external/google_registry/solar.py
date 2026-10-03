"""Contrato interno de viabilidade solar sobre a collection solar."""

from pydantic import ValidationError

from src.core.travel.models import Coordinate
from src.infra.external.google_registry.client import (
    GoogleRegistryClient,
    get_google_registry_client,
)
from src.infra.external.google_registry.errors import (
    RegistryInvalidRequestError,
    RegistryNotFoundError,
    SolarCoverageUnavailableError,
)
from src.infra.external.google_registry.models import SolarViability


class SolarProvider:
    def __init__(self, client: GoogleRegistryClient | None = None) -> None:
        self._client = client

    async def roof_viability(self, coordinate: Coordinate) -> SolarViability:
        try:
            location = Coordinate.model_validate(coordinate)
        except ValidationError as exc:
            raise RegistryInvalidRequestError("coordenadas inválidas para solar") from exc
        try:
            return await (self._client or get_google_registry_client()).request_model(
                "GET",
                "/v1/solar/roof-viability",
                SolarViability,
                params={
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                },
            )
        except RegistryNotFoundError as exc:
            raise SolarCoverageUnavailableError("sem cobertura solar para a localização") from exc


async def get_roof_viability(coordinate: Coordinate) -> SolarViability:
    return await SolarProvider().roof_viability(coordinate)
