from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_name: str = "stock-hanaro API"
    app_env: str = "development"
    app_version: str = "0.1.0"
    git_sha: str = "local"
    database_url: str = "sqlite:///./stock_hanaro.db"
    cors_origins: str = "http://localhost:3000"
    internal_job_secret: str = ""

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
