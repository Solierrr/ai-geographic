"""Integração tipada com as capabilities do google-registry."""

from src.infra.external.google_registry.client import (
    close_google_registry_client,
    get_google_registry_client,
)

__all__ = ["close_google_registry_client", "get_google_registry_client"]
