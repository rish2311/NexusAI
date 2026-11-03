from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://nexusai:nexusai@localhost:5432/nexusai"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-to-a-long-random-string-in-local-dev"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 14

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    llm_provider: str = "gemini"  # gemini | mock

    default_daily_request_quota: int = 50
    default_daily_token_quota: int = 100_000

    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    login_rate_limit_per_minute: int = 20

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
