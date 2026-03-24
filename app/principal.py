from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.categorias import router as roteador_categorias
from app.api.regras import router as roteador_regras
from app.api.saude import router as roteador_saude
from app.api.submissoes import router as roteador_submissoes
from app.api.submissoes_usuario import router as roteador_submissoes_usuario
from app.api.telegram import router as roteador_telegram
from app.api.usuarios import router as roteador_usuarios
from app.bot.cliente_telegram import ClienteTelegram
from app.configuracoes import pegar_configuracoes
from app.db.sessao import SessionLocal
from app.services.dados_iniciais_ufrj_bcc import popular_dados_referencia_ufrj_bcc

configuracoes = pegar_configuracoes()


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    sessao = SessionLocal()
    try:
        popular_dados_referencia_ufrj_bcc(sessao)
    finally:
        sessao.close()

    if configuracoes.telegram_auto_set_webhook:
        ClienteTelegram().sincronizar_webhook()

    yield


app = FastAPI(title=configuracoes.app_name, lifespan=ciclo_de_vida)

app.include_router(roteador_saude)
app.include_router(roteador_usuarios)
app.include_router(roteador_submissoes_usuario)
app.include_router(roteador_categorias)
app.include_router(roteador_regras)
app.include_router(roteador_submissoes)
app.include_router(roteador_telegram)

