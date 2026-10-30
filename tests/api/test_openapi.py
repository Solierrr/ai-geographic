from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.api.app import app, build_openapi
from src.version import VERSION

client = TestClient(app)


def test_contract_follows_the_standard_metadata():
    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "Solaria — ai-geographic"
    assert schema["info"]["version"] == VERSION
    assert schema["info"]["license"]["name"] == "CC0-1.0"
    assert schema["servers"][0]["description"] == "QA"
    assert schema["security"] == [{"bearerAuth": []}]
    assert schema["components"]["securitySchemes"]["bearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }


def test_every_error_response_uses_problem_detail():
    schema = build_openapi(include_internal=True)

    for path in schema["paths"].values():
        for operation in path.values():
            assert "500" in operation["responses"]
            for code, response in operation["responses"].items():
                if code.startswith(("4", "5")):
                    assert list(response["content"]) == ["application/problem+json"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    assert "ProblemDetail" in schema["components"]["schemas"]


def test_health_routes_are_public():
    schema = build_openapi(include_internal=True)

    assert schema["paths"]["/health"]["get"]["security"] == []
    assert schema["paths"]["/ready"]["get"]["security"] == []


def test_exported_contract_matches_the_code():
    exported = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "openapi.yaml").read_text(encoding="utf-8")
    )

    assert exported == build_openapi(include_internal=True)
