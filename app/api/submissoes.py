from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencias import db_session
from app.schemas.submissao import SubmissaoCriacao, SubmissaoLeitura
from app.services.excecoes import ErroDominio
from app.services.servico_submissoes import ServicoSubmissoes

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=SubmissaoLeitura, status_code=status.HTTP_201_CREATED)
def criar_submissao(dados: SubmissaoCriacao, db: Session = Depends(db_session)) -> SubmissaoLeitura:
    try:
        return ServicoSubmissoes(db).criar_submissao(dados)
    except ErroDominio as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{submission_id}", response_model=SubmissaoLeitura)
def pegar_submissao(submission_id: int, db: Session = Depends(db_session)) -> SubmissaoLeitura:
    submissao = ServicoSubmissoes(db).pegar_submissao(submission_id)
    if not submissao:
        raise HTTPException(status_code=404, detail="Submissao nao encontrada.")
    return submissao


@router.post("/{submission_id}/evidences", response_model=SubmissaoLeitura)
def enviar_comprovante(submission_id: int, file: UploadFile = File(...), db: Session = Depends(db_session)) -> SubmissaoLeitura:
    try:
        return ServicoSubmissoes(db).adicionar_comprovante(submission_id, file)
    except ErroDominio as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{submission_id}/evidences/{evidence_id}", response_model=SubmissaoLeitura)
def remover_comprovante(submission_id: int, evidence_id: int, db: Session = Depends(db_session)) -> SubmissaoLeitura:
    try:
        return ServicoSubmissoes(db).remover_comprovante(submission_id, evidence_id)
    except ErroDominio as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_submissao(submission_id: int, db: Session = Depends(db_session)) -> None:
    try:
        ServicoSubmissoes(db).remover_submissao(submission_id)
    except ErroDominio as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

