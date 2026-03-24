from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.sessao import pegar_db


def sessao_db(db: Session = Depends(pegar_db)) -> Session:
    return db


db_session = sessao_db

