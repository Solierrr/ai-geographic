import jwt as pyjwt
from jwt import PyJWKClient

from src.core.config.settings import settings

_jwk_client: PyJWKClient | None = None


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(settings.JWT_JWKS_URL)
    return _jwk_client


def decode_user_id(token: str) -> str | None:
    """Extrai sub (user id) do JWT, RS256 via JWKS do api-auth. None em
    qualquer falha — config ausente, token inválido, claim ausente, ou
    JWKS fora do ar — memória é best-effort, nunca pode derrubar o turno."""
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        payload = pyjwt.decode(
            token, signing_key.key, algorithms=["RS256"], issuer=settings.JWT_ISSUER
        )
        return payload.get("sub")
    except Exception:  # noqa: BLE001
        return None
