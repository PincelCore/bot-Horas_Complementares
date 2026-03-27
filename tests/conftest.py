import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["STORAGE_DIR"] = "./test_storage"
os.environ["STORAGE_BACKEND"] = "filesystem"
os.environ["TELEGRAM_MODE"] = "webhook"

from app.api.dependencias import db_session
from app.db.base import Base
from app.principal import app


URL_BANCO_TESTE = "sqlite:///./test.db"
motor_teste = create_engine(URL_BANCO_TESTE, connect_args={"check_same_thread": False})
SessaoTesteLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor_teste)


@pytest.fixture(autouse=True)
def preparar_banco():
    Base.metadata.drop_all(bind=motor_teste)
    Base.metadata.create_all(bind=motor_teste)
    shutil.rmtree("./test_storage", ignore_errors=True)
    Path("./test_storage").mkdir(exist_ok=True)
    yield
    Base.metadata.drop_all(bind=motor_teste)
    shutil.rmtree("./test_storage", ignore_errors=True)


@pytest.fixture
def db():
    sessao = SessaoTesteLocal()
    try:
        yield sessao
    finally:
        sessao.close()


@pytest.fixture
def client(db):
    def sobrescrever_sessao_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[db_session] = sobrescrever_sessao_db
    with TestClient(app) as cliente_teste:
        yield cliente_teste
    app.dependency_overrides.clear()
