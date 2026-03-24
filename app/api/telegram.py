from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencias import db_session
from app.bot.cliente_telegram import ClienteTelegram
from app.bot.servico_telegram import ServicoTelegram
from app.configuracoes import pegar_configuracoes
from app.schemas.telegram import RespostaInfoWebhookTelegram, RespostaWebhookTelegram, RespostaSincronizacaoWebhookTelegram
from app.services.excecoes import ErroDominio

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook", response_model=RespostaWebhookTelegram)
def webhook_telegram(
    update: dict,
    db: Session = Depends(db_session),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> RespostaWebhookTelegram:
    configuracoes = pegar_configuracoes()
    if configuracoes.telegram_webhook_secret and x_telegram_bot_api_secret_token != configuracoes.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Token secreto do Telegram invalido.")

    mensagem = ServicoTelegram(db).processar_update(update)
    return RespostaWebhookTelegram(message=mensagem)


@router.post("/sync-webhook", response_model=RespostaSincronizacaoWebhookTelegram)
def sincronizar_webhook() -> RespostaSincronizacaoWebhookTelegram:
    try:
        sincronizado = ClienteTelegram().sincronizar_webhook()
    except ErroDominio as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RespostaSincronizacaoWebhookTelegram(synced=sincronizado)


@router.get("/webhook-info", response_model=RespostaInfoWebhookTelegram)
def pegar_info_webhook() -> RespostaInfoWebhookTelegram:
    try:
        info = ClienteTelegram().pegar_info_webhook()
    except ErroDominio as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RespostaInfoWebhookTelegram(**info)

