from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI", "DB_MONGO_URI"),
    )
    CHECKPOINT_TTL_DIAS: int = 30

    # O Infisical guarda o Redis dos agentes como UPSTASH_AGENTS_*.
    UPSTASH_REDIS_HOST: str | None = Field(
        None, validation_alias=AliasChoices("UPSTASH_REDIS_HOST", "UPSTASH_AGENTS_HOST")
    )
    UPSTASH_REDIS_PORT: int = Field(
        6379, validation_alias=AliasChoices("UPSTASH_REDIS_PORT", "UPSTASH_AGENTS_PORT")
    )
    UPSTASH_REDIS_USERNAME: str = Field(
        "default",
        validation_alias=AliasChoices(
            "UPSTASH_REDIS_USERNAME", "UPSTASH_AGENTS_USERNAME"
        ),
    )
    UPSTASH_REDIS_PASSWORD: str | None = Field(
        None,
        validation_alias=AliasChoices(
            "UPSTASH_REDIS_PASSWORD", "UPSTASH_AGENTS_PASSWORD"
        ),
    )

    API_MESSENGER_URL: str | None = None
    SERVICE_KEY: str | None = Field(
        None, validation_alias=AliasChoices("SERVICE_KEY", "SERVICE_KEY_AI_GEOGRAPHIC")
    )

    JWT_JWKS_URL: str | None = None
    JWT_ISSUER: str | None = None

    ENVIRONMENT: str = "LOCAL"

    DEBUG_ADMIN_SUBS: str = ""

    TEST_USER_TOKEN: str | None = (
        None  # só pra uso local via main.py, nunca em produção
    )

    # MCP oficial do Google Maps (Grounding Lite): lugares, clima e rotas.
    MAPS_MCP_URL: str = "https://mapstools.googleapis.com/mcp"
    GOOGLE_MAPS_API_KEY: str | None = None

    # google-registry: viabilidade solar do telhado (Solar API do Google).
    REGISTRY_URL: str = Field(
        "http://localhost:8000",
        validation_alias=AliasChoices("REGISTRY_URL", "GOOGLE_REGISTRY_URL"),
    )
    REGISTRY_CONSUMER_TOKEN: str | None = None

    # A2A: o ai-assistant recebe a delegação de recomendação de produtos.
    A2A_ASSISTANT_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
