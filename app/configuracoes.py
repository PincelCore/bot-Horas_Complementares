from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    app_name: str = "Horas Complementares Bot"
    database_url: str = "sqlite:///./horas_bot.db"
    storage_dir: Path = Path("./storage")
    telegram_bot_token: str = ""
    telegram_api_base_url: str = "https://api.telegram.org"
    telegram_mode: str = "webhook"
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""
    telegram_auto_set_webhook: bool = False
    max_upload_size_mb: int = 10
    allowed_mime_types: list[str] | str = ["application/pdf", "image/jpeg", "image/png"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("allowed_mime_types", mode="before")
    @classmethod
    def split_allowed_mime_types(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalizar_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value


@lru_cache
def pegar_configuracoes() -> Configuracoes:
    configuracoes = Configuracoes()
    configuracoes.storage_dir.mkdir(parents=True, exist_ok=True)
    return configuracoes

