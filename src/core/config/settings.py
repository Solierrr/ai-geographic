from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )
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

    MCP_URL: str = "http://localhost:8001/mcp"
    MCP_API_KEY: str | None = None

    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
