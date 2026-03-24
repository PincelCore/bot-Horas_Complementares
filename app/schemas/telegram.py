from pydantic import BaseModel


class RespostaWebhookTelegram(BaseModel):
    message: str


class RespostaSincronizacaoWebhookTelegram(BaseModel):
    synced: bool


class RespostaInfoWebhookTelegram(BaseModel):
    url: str
    has_custom_certificate: bool | None = None
    pending_update_count: int | None = None
    last_error_date: int | None = None
    last_error_message: str | None = None
    last_synchronization_error_date: int | None = None
    max_connections: int | None = None
    ip_address: str | None = None

