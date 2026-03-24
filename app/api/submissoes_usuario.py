from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencias import db_session
from app.schemas.submissao import SubmissaoLeitura
from app.services.servico_submissoes import ServicoSubmissoes

router = APIRouter(prefix="/users", tags=["submissions"])


@router.get("/{user_id}/submissions", response_model=list[SubmissaoLeitura])
def listar_submissoes_do_usuario(user_id: int, db: Session = Depends(db_session)) -> list[SubmissaoLeitura]:
    return ServicoSubmissoes(db).listar_submissoes_do_usuario(user_id)

