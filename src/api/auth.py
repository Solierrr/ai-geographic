import asyncio

from fastapi import HTTPException

from src.core.config.settings import settings
from src.core.security.jwt import is_valid_access_token


async def require_valid_token(token: str) -> None:
    """Recusa com 401 o token que o api-auth não assinou ou que expirou, antes de gastar
    LLM ou chamar outros serviços. Sem JWKS configurado, só o ambiente LOCAL segue sem
    validar; nos demais a rota falha fechada."""
    if not settings.JWT_JWKS_URL:
        if settings.ENVIRONMENT.upper() == "LOCAL":
            return
        raise HTTPException(
            status_code=503, detail="Validação do access token não configurada"
        )
    if not await asyncio.to_thread(is_valid_access_token, token):
        raise HTTPException(
            status_code=401,
            detail="Access token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
