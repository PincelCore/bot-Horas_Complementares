from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DocumentoRecebido


class RepositorioDocumentosRecebidos:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, documento: DocumentoRecebido) -> DocumentoRecebido:
        self.db.add(documento)
        self.db.flush()
        self.db.refresh(documento)
        return documento

    def pegar(self, documento_id: int) -> DocumentoRecebido | None:
        return self.db.get(DocumentoRecebido, documento_id)

    def contar_por_usuario_desde(self, user_id: int, instante: datetime) -> int:
        consulta = select(func.count(DocumentoRecebido.id)).where(
            DocumentoRecebido.user_id == user_id,
            DocumentoRecebido.created_at >= instante,
        )
        return int(self.db.scalar(consulta) or 0)

    def contar_por_hash(self, file_hash: str) -> int:
        consulta = select(func.count(DocumentoRecebido.id)).where(DocumentoRecebido.file_hash == file_hash)
        return int(self.db.scalar(consulta) or 0)

    def listar_expirados(self, instante: datetime) -> list[DocumentoRecebido]:
        consulta = select(DocumentoRecebido).where(
            DocumentoRecebido.submission_id.is_(None),
            DocumentoRecebido.created_at < instante,
        )
        return list(self.db.scalars(consulta).all())

    def listar_por_submissao(self, submission_id: int) -> list[DocumentoRecebido]:
        consulta = select(DocumentoRecebido).where(DocumentoRecebido.submission_id == submission_id)
        return list(self.db.scalars(consulta).all())

    def remover(self, documento: DocumentoRecebido) -> None:
        self.db.delete(documento)
        self.db.flush()
