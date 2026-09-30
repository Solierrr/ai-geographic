from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from src.core.travel.models import Coordinate


class ChatRequest(BaseModel):
    """O que o cliente envia no POST /chat."""

    conversation_id: str = Field(..., examples=["b2b-empresa-42"])
    message: str = Field(..., min_length=1, examples=["Como vou do Centro ao Ibirapuera de carro agora?"])
    current_location: Coordinate | None = Field(
        default=None,
        description="Coordenadas enviadas pelo app após permissão do usuário.",
    )
    user_timezone: str | None = Field(
        default=None,
        description="Fuso IANA do usuário, usado para interpretar hoje/amanhã; padrão configurado pelo servidor.",
        examples=["America/Sao_Paulo"],
    )

    @field_validator("user_timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Fuso IANA inválido") from exc
        return value


class RouteData(BaseModel):
    route_id: str
    duration_seconds: int = Field(ge=0)
    distance_meters: int = Field(ge=0)
    encoded_polyline: str | None = None
    provider: Literal["google_maps"]


class ChatResponse(BaseModel):
    """O que a API devolve no POST /chat."""

    response: str
    specialists_used: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    route_data: RouteData | None = None
