from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencias import db_session
from app.schemas.usuario import ResumoUsuario, UsuarioCriacao, UsuarioLeitura
from app.services.excecoes import ErroDominio
from app.services.servico_usuarios import ServicoUsuarios

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UsuarioLeitura, status_code=status.HTTP_201_CREATED)
def criar_usuario(dados: UsuarioCriacao, db: Session = Depends(db_session)) -> UsuarioLeitura:
    servico = ServicoUsuarios(db)
    try:
        return servico.criar_usuario(dados)
    except ErroDominio as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{user_id}/summary", response_model=ResumoUsuario)
def resumo_do_usuario(user_id: int, db: Session = Depends(db_session)) -> ResumoUsuario:
    return ServicoUsuarios(db).pegar_resumo(user_id)
