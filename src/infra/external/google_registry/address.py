"""Contrato interno de endereços sobre a collection address do registry."""

from urllib.parse import quote

from pydantic import ValidationError

from src.core.travel.models import Coordinate, ResolvedPlace
from src.infra.external.google_registry.client import (
    GoogleRegistryClient,
    get_google_registry_client,
)
from src.infra.external.google_registry.errors import RegistryInvalidRequestError
from src.infra.external.google_registry.models import (
    AddressListResponse,
    GeocodeRequest,
    RegistryAddress,
    ResolveRequest,
    ResolveResponse,
    ReverseGeocodeRequest,
    Suggestion,
    SuggestionsRequest,
    SuggestionsResponse,
    ValidateRequest,
    ValidateResponse,
)


class AddressProvider:
    def __init__(self, client: GoogleRegistryClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> GoogleRegistryClient:
        return self._client or get_google_registry_client()

    async def suggestions(
        self,
        query: str,
        *,
        session_token: str | None = None,
        language: str = "pt-BR",
        country: str = "BR",
    ) -> list[Suggestion]:
        request = _validated(
            SuggestionsRequest,
            query=query,
            session_token=session_token,
            language=language,
            country=country,
        )
        response = await self.client.request_model(
            "POST",
            "/v1/address/suggestions",
            SuggestionsResponse,
            json=request.model_dump(exclude_none=True),
        )
        return response.suggestions

    async def get_place(
        self,
        place_id: str,
        *,
        session_token: str | None = None,
        language: str = "pt-BR",
    ) -> RegistryAddress:
        return await self.client.request_model(
            "GET",
            f"/v1/address/places/{quote(place_id, safe='')}",
            RegistryAddress,
            params={
                key: value
                for key, value in {
                    "session_token": session_token,
                    "language": language,
                }.items()
                if value is not None
            },
        )

    async def geocode(self, address: str, *, language: str = "pt-BR") -> list[RegistryAddress]:
        request = _validated(GeocodeRequest, address=address, language=language)
        response = await self.client.request_model(
            "POST",
            "/v1/address/geocode",
            AddressListResponse,
            json=request.model_dump(),
        )
        return response.results

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        *,
        language: str = "pt-BR",
    ) -> list[RegistryAddress]:
        request = _validated(
            ReverseGeocodeRequest,
            latitude=latitude,
            longitude=longitude,
            language=language,
        )
        response = await self.client.request_model(
            "POST",
            "/v1/address/reverse-geocode",
            AddressListResponse,
            json=request.model_dump(),
        )
        return response.results

    async def validate(self, request: ValidateRequest) -> ValidateResponse:
        return await self.client.request_model(
            "POST",
            "/v1/address/validate",
            ValidateResponse,
            json=request.model_dump(exclude_none=True),
        )

    async def resolve(
        self,
        *,
        place_id: str | None = None,
        query: str | None = None,
        session_token: str | None = None,
        language: str = "pt-BR",
    ) -> ResolveResponse:
        request = _validated(
            ResolveRequest,
            place_id=place_id,
            query=query,
            session_token=session_token,
            language=language,
        )
        return await self.client.request_model(
            "POST",
            "/v1/address/resolve",
            ResolveResponse,
            json=request.model_dump(exclude_none=True),
        )

    async def search(self, query: str, *, language: str = "pt-BR") -> list[ResolvedPlace]:
        """Usa autocomplete de endereço; geocode é fallback, não Text Search."""
        suggestions = await self.suggestions(query, language=language)
        if suggestions:
            addresses = [
                await self.get_place(item.place_id, language=language)
                for item in suggestions[:3]
            ]
            labels = [item.main_text or item.description for item in suggestions[:3]]
            return [
                _to_resolved(address, label=label)
                for address, label in zip(addresses, labels, strict=True)
            ]
        geocoded = await self.geocode(query, language=language)
        return [_to_resolved(address) for address in geocoded[:3]]


def _validated(model_type, **values):
    try:
        return model_type.model_validate(values)
    except ValidationError as exc:
        raise RegistryInvalidRequestError("parâmetros inválidos para address") from exc


def _to_resolved(address: RegistryAddress, *, label: str | None = None) -> ResolvedPlace:
    return ResolvedPlace(
        label=label or address.formatted_address,
        address=address.formatted_address,
        coordinate=Coordinate(latitude=address.latitude, longitude=address.longitude),
        place_id=address.place_id,
    )


async def search_places(query: str, *, language: str = "pt-BR") -> list[ResolvedPlace]:
    return await AddressProvider().search(query, language=language)


async def place_by_id(place_id: str, *, language: str = "pt-BR") -> ResolvedPlace:
    return _to_resolved(await AddressProvider().get_place(place_id, language=language))
