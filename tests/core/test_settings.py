import pytest

from src.core.config.settings import Settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("DB_MONGO_AGENTS", raising=False)


def test_agents_database_defaults_to_dbagents():
    assert Settings(_env_file=None).DB_MONGO_AGENTS == "dbagents"


def test_agents_database_reads_env(monkeypatch):
    monkeypatch.setenv("DB_MONGO_AGENTS", "dbagentsqa")

    assert Settings(_env_file=None).DB_MONGO_AGENTS == "dbagentsqa"
