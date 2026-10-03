"""DTOs do contrato público consumido no google-registry."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RegistryAddress(BaseModel):
    place_id: str | None = None
    formatted_address: str
    street_name: str | None = None
    street_number: str | None = None
    complement: str | None = None
    neighborhood: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country_code: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    precision: Literal["rooftop", "interpolated", "center", "approximate"] | None = None
    partial_match: bool = False


class Suggestion(BaseModel):
    place_id: str
    description: str
    main_text: str | None = None
    secondary_text: str | None = None


class SuggestionsRequest(BaseModel):
    query: str = Field(min_length=3)
    session_token: str | None = None
    language: str = "pt-BR"
    country: str = "BR"


class SuggestionsResponse(BaseModel):
    suggestions: list[Suggestion]


class GeocodeRequest(BaseModel):
    address: str = Field(min_length=3)
    language: str = "pt-BR"


class ReverseGeocodeRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    language: str = "pt-BR"


class AddressListResponse(BaseModel):
    results: list[RegistryAddress]


class ValidateRequest(BaseModel):
    address_lines: list[str] = Field(min_length=1, max_length=10)
    postal_code: str | None = None
    locality: str | None = None
    administrative_area: str | None = None
    region_code: str = "BR"


class AddressValidation(BaseModel):
    verdict: Literal["ok", "needs_review", "invalid"]
    missing_components: list[str] = Field(default_factory=list)
    unconfirmed_components: list[str] = Field(default_factory=list)


class ValidateResponse(AddressValidation):
    address: RegistryAddress | None = None


class ResolveRequest(BaseModel):
    place_id: str | None = None
    query: str | None = Field(default=None, min_length=3)
    session_token: str | None = None
    language: str = "pt-BR"

    @model_validator(mode="after")
    def exactly_one_location(self) -> "ResolveRequest":
        if (self.place_id is None) == (self.query is None):
            raise ValueError("informe exatamente um entre place_id e query")
        return self


class ResolveResponse(BaseModel):
    address: RegistryAddress
    validation: AddressValidation | None = None


class TimezoneResponse(BaseModel):
    timezone_id: str
    utc_offset_seconds: int


class RoofSegment(BaseModel):
    pitch_degrees: float
    azimuth_degrees: float
    area_m2: float = Field(ge=0)


class SolarPanelConfig(BaseModel):
    panels_count: int = Field(ge=0)
    yearly_energy_dc_kwh: float = Field(ge=0)


class SolarViability(BaseModel):
    imagery_date: str
    usable_roof_area_m2: float = Field(ge=0)
    max_panel_count: int = Field(ge=0)
    annual_sunshine_hours: float = Field(ge=0)
    carbon_offset_factor_kg_mwh: float = Field(ge=0)
    roof_segments: list[RoofSegment]
    panel_capacity_watts: float | None = Field(default=None, ge=0)
    panel_width_meters: float | None = Field(default=None, ge=0)
    panel_height_meters: float | None = Field(default=None, ge=0)
    panel_configs: list[SolarPanelConfig] = Field(default_factory=list)
