from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.configuracoes import pegar_configuracoes


configuracoes = pegar_configuracoes()
argumentos_conexao = {"check_same_thread": False} if configuracoes.database_url.startswith("sqlite") else {}
engine = create_engine(configuracoes.database_url, future=True, connect_args=argumentos_conexao)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def pegar_db() -> Generator[Session, None, None]:
    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()

