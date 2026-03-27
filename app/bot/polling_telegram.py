from __future__ import annotations

import threading
import time

from app.bot.cliente_telegram import ClienteTelegram
from app.bot.servico_telegram import ServicoTelegram
from app.configuracoes import pegar_configuracoes
from app.db.sessao import SessionLocal


class WorkerPollingTelegram:
    def __init__(self) -> None:
        self.configuracoes = pegar_configuracoes()
        self.cliente = ClienteTelegram()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._ultimo_update_id: int | None = None

    def iniciar(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.cliente.remover_webhook()
        self._thread = threading.Thread(target=self._loop, name="telegram-polling-worker", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.configuracoes.telegram_polling_sleep_seconds + 1)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                updates = self.cliente.buscar_updates(
                    offset=self._ultimo_update_id,
                    timeout=self.configuracoes.telegram_polling_timeout_seconds,
                )
                for update in updates:
                    self._processar_update(update)
                    self._ultimo_update_id = int(update["update_id"]) + 1
            except Exception:
                time.sleep(self.configuracoes.telegram_polling_sleep_seconds)

    def _processar_update(self, update: dict) -> None:
        sessao = SessionLocal()
        try:
            ServicoTelegram(sessao).processar_update(update)
        finally:
            sessao.close()
