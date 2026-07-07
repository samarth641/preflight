"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PREFLIGHT_", env_file=".env")

    app_name: str = "Preflight"
    app_version: str = "0.1.0"
    debug: bool = False
    knowledge_root: Path | None = None
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "preflight"
    default_engine_plugin: str = "rule-based"


settings = Settings()
