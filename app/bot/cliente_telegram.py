from __future__ import annotations

from typing import Any

import httpx

from app.configuracoes import pegar_configuracoes
from app.services.excecoes import ErroDominio


class ClienteTelegram:
    def __init__(self) -> None:
        self.configuracoes = pegar_configuracoes()

    @property
    def ativo(self) -> bool:
        return bool(self.configuracoes.telegram_bot_token)

    def enviar_mensagem(self, chat_id: int, texto: str, marcacao: dict[str, Any] | None = None) -> None:
        if not self.ativo:
            return
        carga = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}
        if marcacao:
            carga["reply_markup"] = marcacao
        self._fazer_requisicao_json("sendMessage", carga)

    def send_message(self, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        self.enviar_mensagem(chat_id, text, marcacao=reply_markup)

    def responder_callback(self, callback_id: str, texto: str | None = None) -> None:
        if not self.ativo:
            return
        carga: dict[str, Any] = {"callback_query_id": callback_id}
        if texto:
            carga["text"] = texto
        self._fazer_requisicao_json("answerCallbackQuery", carga)

    def answer_callback_query(self, callback_id: str, text: str | None = None) -> None:
        self.responder_callback(callback_id, texto=text)

    def buscar_arquivo(self, file_id: str) -> dict[str, Any]:
        if not self.ativo:
            raise ErroDominio("Token do Telegram nao configurado.")
        return self._fazer_requisicao_json("getFile", {"file_id": file_id})

    def get_file(self, file_id: str) -> dict[str, Any]:
        return self.buscar_arquivo(file_id)

    def baixar_arquivo(self, caminho_arquivo: str) -> bytes:
        if not self.ativo:
            raise ErroDominio("Token do Telegram nao configurado.")
        url_base = self.configuracoes.telegram_api_base_url.rstrip("/")
        token = self.configuracoes.telegram_bot_token
        url = f"{url_base}/file/bot{token}/{caminho_arquivo}"
        with httpx.Client(timeout=30.0) as cliente_http:
            resposta = cliente_http.get(url)
            resposta.raise_for_status()
            return resposta.content

    def download_file(self, file_path: str) -> bytes:
        return self.baixar_arquivo(file_path)

    def sincronizar_webhook(self) -> bool:
        if not self.ativo or not self.configuracoes.telegram_webhook_url:
            return False
        carga: dict[str, Any] = {"url": self.configuracoes.telegram_webhook_url}
        if self.configuracoes.telegram_webhook_secret:
            carga["secret_token"] = self.configuracoes.telegram_webhook_secret
        resultado = self._fazer_requisicao_json("setWebhook", carga)
        return bool(resultado)

    def set_webhook(self) -> bool:
        return self.sincronizar_webhook()

    def remover_webhook(self, descartar_updates_pendentes: bool = False) -> bool:
        if not self.ativo:
            return False
        resultado = self._fazer_requisicao_json("deleteWebhook", {"drop_pending_updates": descartar_updates_pendentes})
        return bool(resultado)

    def delete_webhook(self, drop_pending_updates: bool = False) -> bool:
        return self.remover_webhook(drop_pending_updates)

    def pegar_info_webhook(self) -> dict[str, Any]:
        if not self.ativo:
            raise ErroDominio("Token do Telegram nao configurado.")
        return self._fazer_requisicao_json("getWebhookInfo", {})

    def get_webhook_info(self) -> dict[str, Any]:
        return self.pegar_info_webhook()

    def buscar_updates(self, *, offset: int | None = None, timeout: int | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        if not self.ativo:
            raise ErroDominio("Token do Telegram nao configurado.")
        carga: dict[str, Any] = {}
        if offset is not None:
            carga["offset"] = offset
        if timeout is not None:
            carga["timeout"] = timeout
        if limit is not None:
            carga["limit"] = limit
        return list(self._fazer_requisicao_json("getUpdates", carga) or [])

    def get_updates(self, *, offset: int | None = None, timeout: int | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        return self.buscar_updates(offset=offset, timeout=timeout, limit=limit)

    def _fazer_requisicao_json(self, metodo: str, carga: dict[str, Any]) -> Any:
        url_base = self.configuracoes.telegram_api_base_url.rstrip("/")
        token = self.configuracoes.telegram_bot_token
        url = f"{url_base}/bot{token}/{metodo}"
        with httpx.Client(timeout=30.0) as cliente_http:
            resposta = cliente_http.post(url, json=carga)
            resposta.raise_for_status()
            dados = resposta.json()
        if not dados.get("ok"):
            raise ErroDominio(dados.get("description", f"Falha ao chamar {metodo} no Telegram."))
        return dados.get("result")


TelegramBotApiClient = ClienteTelegram

