from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )
    DB_MONGO_AGENTS: str = "dbagents"
    CHECKPOINT_TTL_DIAS: int = 30

    UPSTASH_REDIS_HOST: str | None = None
    UPSTASH_REDIS_PORT: int = 6379
    UPSTASH_REDIS_USERNAME: str = "default"
    UPSTASH_REDIS_PASSWORD: str | None = None

    API_MESSENGER_URL: str | None = None

    JWT_JWKS_URL: str | None = None
    JWT_ISSUER: str | None = None

    ENVIRONMENT: str = "LOCAL"

    TEST_USER_TOKEN: str | None = (
        None  # só pra uso local via main.py, nunca em produção
    )

    # MCP oficial do Google Maps (Grounding Lite): lugares, clima e rotas.
    MAPS_MCP_URL: str = "https://mapstools.googleapis.com/mcp"
    GOOGLE_MAPS_API_KEY: str | None = None

    # google-registry: viabilidade solar do telhado (Solar API do Google).
    REGISTRY_URL: str = "http://localhost:8004"
    REGISTRY_CONSUMER_TOKEN: str | None = None

    # A2A: o ai-assistant recebe a delegação de recomendação de produtos.
    A2A_ASSISTANT_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
