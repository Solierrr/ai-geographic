from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.errors import ApiError, register_error_handlers

client = TestClient(app)

_PROBLEM_FIELDS = {"type", "title", "status", "errorCode", "detail", "instance", "timestamp"}


def _assert_problem(response, status: int, error_code: str, instance: str) -> dict:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert _PROBLEM_FIELDS <= body.keys()
    assert body["type"] == "about:blank"
    assert body["title"] == error_code
    assert body["errorCode"] == error_code
    assert body["status"] == status
    assert body["instance"] == instance
    return body


def test_missing_authorization_returns_unauthenticated_problem():
    response = client.post("/chat", json={"conversation_id": "conv-1", "message": "oi"})

    _assert_problem(response, 401, "UNAUTHENTICATED", "/chat")


def test_invalid_body_returns_validation_problem_with_fields():
    response = client.post(
        "/chat",
        json={"conversation_id": "conv-1", "message": ""},
        headers={"Authorization": "Bearer token"},
    )

    body = _assert_problem(response, 422, "VALIDATION_FAILED", "/chat")
    assert body["errors"][0]["field"] == "message"
    assert body["errors"][0]["errorCode"] == "VALIDATION_FAILED"


def test_unknown_route_returns_not_found_problem():
    response = client.get("/nao-existe")

    _assert_problem(response, 404, "NOT_FOUND", "/nao-existe")


def _app_with_failing_routes() -> FastAPI:
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/api-error")
    async def api_error():
        raise ApiError(409, "CONFLICT", "Conflito de estado.")

    @test_app.get("/http-error")
    async def http_error():
        raise HTTPException(status_code=403, detail="Sem permissão.")

    @test_app.get("/boom")
    async def boom():
        raise RuntimeError("falha inesperada")

    return test_app


def test_api_error_keeps_its_code():
    test_client = TestClient(_app_with_failing_routes())

    _assert_problem(test_client.get("/api-error"), 409, "CONFLICT", "/api-error")
    _assert_problem(test_client.get("/http-error"), 403, "FORBIDDEN", "/http-error")


def test_unexpected_error_returns_internal_error_problem():
    test_client = TestClient(_app_with_failing_routes(), raise_server_exceptions=False)

    body = _assert_problem(test_client.get("/boom"), 500, "INTERNAL_ERROR", "/boom")
    assert "falha inesperada" not in body["detail"]
