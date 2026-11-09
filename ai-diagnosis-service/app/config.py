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

    # SQLAlchemy
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
