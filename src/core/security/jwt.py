from ai_lib.security import decode_user_id as _decode_user_id

from src.core.config.settings import settings


def decode_user_id(token: str) -> str | None:
    """Extrai sub (user id) do JWT, RS256 via JWKS do api-auth. None em
    qualquer falha — config ausente, token inválido, claim ausente, ou
    JWKS fora do ar — memória é best-effort, nunca pode derrubar o turno."""
    if not settings.JWT_JWKS_URL or not settings.JWT_ISSUER:
        return None
    return _decode_user_id(
        token, jwks_url=settings.JWT_JWKS_URL, issuer=settings.JWT_ISSUER
    )
