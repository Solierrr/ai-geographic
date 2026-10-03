"""Contrato estável do workflow para a implementação local de Weather."""

from src.infra.external.google_geographic import hourly_weather

__all__ = ["hourly_weather"]
