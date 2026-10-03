from functools import lru_cache

from ai_lib.registry import RegistryClient, RegistryError

from src.core.config.settings import settings


@lru_cache(maxsize=1)
def registry_client() -> RegistryClient:
    if not settings.GOOGLE_REGISTRY_URL or not settings.REGISTRY_CONSUMER_TOKEN:
        raise RegistryError(
            "GOOGLE_REGISTRY_URL and REGISTRY_CONSUMER_TOKEN must be set"
        )
    return RegistryClient(
        settings.GOOGLE_REGISTRY_URL, settings.REGISTRY_CONSUMER_TOKEN
    )
