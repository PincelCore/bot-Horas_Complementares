from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    app_name: str = "Horas Complementares Bot"
    database_url: str = "sqlite:///./horas_bot.db"
    storage_dir: Path = Path("./storage")
    storage_backend: str = "filesystem"
    storage_bucket: str = ""
    storage_region: str = "auto"
    storage_endpoint_url: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    storage_key_prefix: str = "evidences"
    telegram_bot_token: str = ""
    telegram_api_base_url: str = "https://api.telegram.org"
    telegram_mode: str = "webhook"
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""
    telegram_auto_set_webhook: bool = False
    telegram_polling_timeout_seconds: int = 25
    telegram_polling_sleep_seconds: float = 1.0
    max_upload_size_mb: int = 10
    max_evidences_per_submission: int = 3
    max_documents_per_user_per_hour: int = 12
    max_documents_per_user_per_day: int = 30
    incoming_document_retention_days: int = 14
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

    @field_validator("storage_backend", mode="before")
    @classmethod
    def normalizar_storage_backend(cls, value: str) -> str:
        backend = (value or "filesystem").strip().lower()
        if backend not in {"filesystem", "s3"}:
            raise ValueError("STORAGE_BACKEND deve ser 'filesystem' ou 's3'.")
        return backend

    @field_validator("telegram_mode", mode="before")
    @classmethod
    def normalizar_telegram_mode(cls, value: str) -> str:
        modo = (value or "webhook").strip().lower()
        if modo not in {"webhook", "polling"}:
            raise ValueError("TELEGRAM_MODE deve ser 'webhook' ou 'polling'.")
        return modo


@lru_cache
def pegar_configuracoes() -> Configuracoes:
    configuracoes = Configuracoes()
    configuracoes.storage_dir.mkdir(parents=True, exist_ok=True)
    return configuracoes

