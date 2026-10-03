"""Erros estáveis expostos pela integração com o google-registry."""


class GoogleRegistryError(Exception):
    """Erro base sem detalhes de transporte ou infraestrutura."""

    kind = "registry_error"


class RegistryInvalidRequestError(GoogleRegistryError):
    kind = "invalid_request"


class RegistryNotFoundError(GoogleRegistryError):
    kind = "not_found"


class AddressAmbiguousError(GoogleRegistryError):
    kind = "ambiguous_address"


class SolarCoverageUnavailableError(RegistryNotFoundError):
    kind = "solar_coverage_unavailable"


class RegistryQuotaExceededError(GoogleRegistryError):
    kind = "quota"


class RegistryTimeoutError(GoogleRegistryError):
    kind = "timeout"


class RegistryUnavailableError(GoogleRegistryError):
    kind = "unavailable"


class RegistryAuthenticationError(GoogleRegistryError):
    kind = "authentication"


class RegistryInvalidResponseError(GoogleRegistryError):
    kind = "invalid_response"
