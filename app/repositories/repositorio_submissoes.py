from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Submissao, SubmissaoComprovante


class RepositorioSubmissoes:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, submissao: Submissao) -> Submissao:
        self.db.add(submissao)
        self.db.flush()
        self.db.refresh(submissao)
        return submissao

    def pegar(self, id_submissao: int) -> Submissao | None:
        consulta = (
            select(Submissao)
            .options(joinedload(Submissao.category), joinedload(Submissao.evidences).joinedload(SubmissaoComprovante.evidence))
            .where(Submissao.id == id_submissao)
        )
        return self.db.scalar(consulta)

    def listar_por_usuario(self, id_usuario: int) -> list[Submissao]:
        consulta = (
            select(Submissao)
            .options(joinedload(Submissao.category), joinedload(Submissao.evidences).joinedload(SubmissaoComprovante.evidence))
            .where(Submissao.user_id == id_usuario)
            .order_by(Submissao.created_at.desc())
        )
        return list(self.db.scalars(consulta).unique().all())

    def somar_horas_estimadas_do_usuario_na_categoria(
        self,
        id_usuario: int,
        id_categoria: int,
        id_submissao_ignorada: int | None = None,
    ) -> float:
        consulta = select(func.coalesce(func.sum(Submissao.estimated_hours), 0.0)).where(
            Submissao.user_id == id_usuario,
            Submissao.category_id == id_categoria,
        )
        if id_submissao_ignorada is not None:
            consulta = consulta.where(Submissao.id != id_submissao_ignorada)
        valor = self.db.scalar(consulta)
        return float(valor or 0.0)

    def create(self, submission: Submissao) -> Submissao:
        return self.criar(submission)

    def get(self, submission_id: int) -> Submissao | None:
        return self.pegar(submission_id)

    def remover(self, submissao: Submissao) -> None:
        self.db.delete(submissao)

    def list_by_user(self, user_id: int) -> list[Submissao]:
        return self.listar_por_usuario(user_id)

    def total_estimated_hours_for_user_category(self, user_id: int, category_id: int, exclude_submission_id: int | None = None) -> float:
        return self.somar_horas_estimadas_do_usuario_na_categoria(user_id, category_id, exclude_submission_id)

    def delete(self, submission: Submissao) -> None:
        self.remover(submission)

