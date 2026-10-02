from unittest.mock import Mock

import pytest

import src.core.security.jwt as jwt_module
from src.core.security.jwt import decode_user_id


@pytest.fixture(autouse=True)
def _jwt_settings(monkeypatch):
    monkeypatch.setattr(jwt_module.settings, "JWT_JWKS_URL", "http://jwks.test/keys")
    monkeypatch.setattr(jwt_module.settings, "JWT_ISSUER", "solaria-auth")


def test_decode_user_id_delega_para_a_lib_com_jwks_e_issuer_do_settings(monkeypatch):
    decode = Mock(return_value="user-123")
    monkeypatch.setattr(jwt_module, "_decode_user_id", decode)

    assert decode_user_id("token-qualquer") == "user-123"
    decode.assert_called_once_with(
        "token-qualquer", jwks_url="http://jwks.test/keys", issuer="solaria-auth"
    )


def test_decode_user_id_retorna_none_com_token_invalido():
    assert decode_user_id("token-invalido") is None


def test_decode_user_id_retorna_none_sem_jwks_url(monkeypatch):
    monkeypatch.setattr(jwt_module.settings, "JWT_JWKS_URL", None)
    decode = Mock()
    monkeypatch.setattr(jwt_module, "_decode_user_id", decode)

    assert decode_user_id("qualquer-token") is None
    decode.assert_not_called()


def test_decode_user_id_retorna_none_sem_issuer(monkeypatch):
    monkeypatch.setattr(jwt_module.settings, "JWT_ISSUER", None)

    assert decode_user_id("qualquer-token") is None
