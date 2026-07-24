from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_env: str = "development"
    app_version: str = "0.1.0"
    git_sha: str = "unknown"
    algorithm_version: str = "unimplemented"
    threshold_config_version: str = "v1"
    gps_max_accuracy_m: float = Field(default=30.0, gt=0)
    gps_max_speed_kmh: float = Field(default=120.0, gt=0)
    routing_data_version: str = "not_configured"
    database_url: str = (
        "postgresql+psycopg://route_app:route_dev_only@localhost:5432/route_deviation"
    )
    redis_url: str = "redis://localhost:6379/0"
    redis_stream_name: str = "route-deviation:events"
    redis_dead_letter_stream_name: str = "route-deviation:dead-letter"
    osrm_url: str | None = None
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def reject_production_wildcard(cls, value: list[str], info: object) -> list[str]:
        if "*" in value:
            raise ValueError("CORS wildcard is not allowed")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
