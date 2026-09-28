"""Mock-IdP mínimo pra ambientes onde o api-auth de verdade ainda não
existe (local ou QA). Serve JWKS e emite tokens de teste assinados.

NUNCA aponte produção pra isso. Serve só pra api-messenger ter algo real
pra validar enquanto o api-auth de verdade não existe/não está deployado
nesse ambiente.
"""

import base64
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI

app = FastAPI(title="mock-idp (dev/qa only)")

_chave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_pem_privada = _chave_privada.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()


def _base64url_uint(n: int) -> str:
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


@app.get("/.well-known/jwks.json")
def jwks():
    numeros = _chave_privada.public_key().public_numbers()
    return {
        "keys": [{
            "kty": "RSA", "use": "sig", "alg": "RS256", "kid": "mock-idp-1",
            "n": _base64url_uint(numeros.n),
            "e": _base64url_uint(numeros.e),
        }]
    }


@app.post("/mint-test-token")
def mint_test_token(sub: str | None = None):
    """Devolve um JWT válido. `sub` opcional, gera um UUID aleatório se
    não informado (simula um usuário diferente por chamada)."""
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": sub or str(uuid.uuid4()),
        "iss": "solaria-auth",
        "token_type": "access",
        "iat": agora,
        "exp": agora + timedelta(hours=1),
    }
    token = jwt.encode(payload, _pem_privada, algorithm="RS256", headers={"kid": "mock-idp-1"})
    return {"access_token": token, "sub": payload["sub"], "expires_in": 3600}
