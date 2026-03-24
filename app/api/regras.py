from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencias import db_session
from app.schemas.regra import RegraLeitura
from app.services.servico_regras import ServicoRegras

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RegraLeitura])
def listar_regras(db: Session = Depends(db_session)) -> list[RegraLeitura]:
    return ServicoRegras(db).listar_regras()

