from unittest.mock import Mock

import jwt as pyjwt
import pytest

import src.core.security.jwt as jwt_module
from src.core.security.jwt import decode_user_id


@pytest.fixture(autouse=True)
def _reset_jwk_client_singleton():
    jwt_module._jwk_client = None
    yield
    jwt_module._jwk_client = None


def test_decode_user_id_retorna_sub_com_token_valido(monkeypatch):
    signing_key = Mock(key="chave-publica-fake")
    jwk_client = Mock()
    jwk_client.get_signing_key_from_jwt.return_value = signing_key
    monkeypatch.setattr(jwt_module, "_get_jwk_client", lambda: jwk_client)
    monkeypatch.setattr(jwt_module.pyjwt, "decode", lambda *a, **k: {"sub": "user-123"})

    assert decode_user_id("token-qualquer") == "user-123"


def test_decode_user_id_retorna_none_com_token_invalido(monkeypatch):
    jwk_client = Mock()
    jwk_client.get_signing_key_from_jwt.side_effect = pyjwt.exceptions.DecodeError(
        "token malformado"
    )
    monkeypatch.setattr(jwt_module, "_get_jwk_client", lambda: jwk_client)

    assert decode_user_id("token-invalido") is None


def test_decode_user_id_retorna_none_com_jwks_url_ausente(monkeypatch):
    monkeypatch.setattr(jwt_module.settings, "JWT_JWKS_URL", None)

    assert decode_user_id("qualquer-token") is None


def test_decode_user_id_retorna_none_com_jwks_fora_do_ar(monkeypatch):
    jwk_client = Mock()
    jwk_client.get_signing_key_from_jwt.side_effect = (
        pyjwt.exceptions.PyJWKClientConnectionError("conexao recusada")
    )
    monkeypatch.setattr(jwt_module, "_get_jwk_client", lambda: jwk_client)

    assert decode_user_id("token-qualquer") is None


def test_decode_user_id_retorna_none_quando_claim_sub_ausente(monkeypatch):
    signing_key = Mock(key="chave-publica-fake")
    jwk_client = Mock()
    jwk_client.get_signing_key_from_jwt.return_value = signing_key
    monkeypatch.setattr(jwt_module, "_get_jwk_client", lambda: jwk_client)
    monkeypatch.setattr(
        jwt_module.pyjwt, "decode", lambda *a, **k: {"iss": "solaria-auth"}
    )

    assert decode_user_id("token-sem-sub") is None
