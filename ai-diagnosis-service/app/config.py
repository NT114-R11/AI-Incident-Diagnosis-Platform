from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "AI Diagnosis Service"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "postgres"
    database_user: str = "postgres"
    database_password: str = Field(default="")

    # Prometheus
    prometheus_url: str = "http://localhost:9090"
    prometheus_timeout_seconds: float = 10.0

    # Loki
    loki_url: str = "http://localhost:3100"
    loki_timeout_seconds: float = 10.0
    loki_tenant_id: str = "fake"

    # SQLAlchemy
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30

    # Gemini
    gemini_api_key: str = Field(default="")
    gemini_primary_model: str = Field(default="")
    gemini_fallback_model: str = Field(default="")
    gemini_fallback_enabled: bool = True
    gemini_timeout_seconds: float = Field(default=30.0, gt=0)

    # Telegram
    telegram_enabled: bool = False
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")
    telegram_timeout_seconds: float = Field(default=10.0, gt=0)
    telegram_admin_ids: str = Field(default="")
    # Evidence collection
    max_evidence_age_minutes: int = Field(default=10, ge=1)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        from sqlalchemy import URL

        return URL.create(
            drivername="postgresql+psycopg",
            username=self.database_user,
            password=self.database_password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        ).render_as_string(hide_password=False)

    @property
    def telegram_admin_id_list(self) -> set[int]:
        return {
            int(admin_id.strip())
            for admin_id in self.telegram_admin_ids.split(",")
            if admin_id.strip()
        }
        
@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()