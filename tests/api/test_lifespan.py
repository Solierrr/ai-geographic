from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient


def test_lifespan_initializes_and_closes_registry_client():
    with (
        patch("src.api.app.ensure_user_memory_indexes", new=AsyncMock()),
        patch("src.api.app.get_google_registry_client", new=Mock()) as get_client,
        patch(
            "src.api.app.close_google_registry_client", new=AsyncMock()
        ) as close_client,
    ):
        from src.api.app import app

        with TestClient(app):
            pass

    get_client.assert_called_once_with()
    close_client.assert_awaited_once_with()
