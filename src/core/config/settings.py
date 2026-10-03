from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_MONGO_URI: str = "mongodb://localhost:27017"
    CHECKPOINT_TTL_DIAS: int = 30

    UPSTASH_AGENTS_HOST: str | None = None
    UPSTASH_AGENTS_PORT: int = 6379
    UPSTASH_AGENTS_USERNAME: str = "default"

    API_MESSENGER_URL: str | None = None
    SERVICE_CLIENT_SECRET: str | None = None

    JWT_JWK_SET_URI: str | None = None
    JWT_ISSUER: str | None = None

    ENVIRONMENT: str = "LOCAL"

    TEST_USER_TOKEN: str | None = (
        None  # só pra uso local via main.py, nunca em produção
    )

    MCP_URL: str = "http://localhost:8001/mcp"
    MCP_API_KEY: str | None = None

    GOOGLE_REGISTRY_URL: str = "http://localhost:8010"
    GOOGLE_REGISTRY_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0)
    REGISTRY_CONSUMER_TOKEN: str | None = None

    GOOGLE_MAPS_API_KEY: str | None = None
    DEFAULT_TIMEZONE: str = "America/Sao_Paulo"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
