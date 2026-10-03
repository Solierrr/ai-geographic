from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class TripIntent(BaseModel):
    intent: Literal[
        "route", "locate", "timezone", "solar", "clarify", "out_of_scope"
    ]
    response_language: Literal["pt-BR", "en", "es"] = "pt-BR"
    origin: str | None = None
    destination: str | None = None
    mode: Literal["DRIVE", "WALK", "TRANSIT", "BICYCLE", "OTHER"] | None = None
    time_kind: Literal["now", "departure", "arrival", "window"] = "now"
    local_time: str | None = None
    window_start: str | None = None
    window_end: str | None = None
    clarification: str | None = None
    selected_place_id: str | None = None
    has_waypoints: bool = False
    needs_hazard_avoidance: bool = False
    avoid_tolls: bool = False
    avoid_highways: bool = False

    @field_validator("origin", "destination", "clarification")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ResolvedPlace(BaseModel):
    label: str
    address: str
    coordinate: Coordinate
    place_id: str | None = None


class RouteOption(BaseModel):
    route_id: str
    duration_seconds: int = Field(ge=0)
    distance_meters: int = Field(ge=0)
    departure_at: datetime
    arrival_at: datetime
    encoded_polyline: str | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WeatherEvidence(BaseModel):
    role: Literal["origin", "destination", "midpoint"]
    route_id: str
    at: datetime
    interval_start: datetime
    interval_end: datetime
    precipitation_probability: int | None = Field(default=None, ge=0, le=100)
    condition: str | None = None
    fetched_at: datetime


class RouteDecision(BaseModel):
    route_id: str
    rationale: Literal["shortest_time", "user_preference", "weather"]
    weather_used: bool = False
