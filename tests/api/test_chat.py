from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_chat_rejects_missing_fields():
    response = client.post("/chat", json={"batata": 1})

    assert response.status_code == 422


def test_chat_rejects_empty_message():
    response = client.post("/chat", json={"conversation_id": "conv-1", "message": ""})

    assert response.status_code == 422


def test_chat_rejects_missing_authorization_header():
    response = client.post(
        "/chat", json={"conversation_id": "conv-1", "message": "oi"}
    )

    assert response.status_code == 401


def test_chat_rejects_malformed_authorization_header():
    response = client.post(
        "/chat",
        json={"conversation_id": "conv-1", "message": "oi"},
        headers={"Authorization": "token-sem-bearer"},
    )

    assert response.status_code == 401
