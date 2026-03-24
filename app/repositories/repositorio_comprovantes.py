from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Comprovante, SubmissaoComprovante


class RepositorioComprovantes:
    def __init__(self, db: Session):
        self.db = db

    def pegar_por_hash(self, hash_arquivo: str) -> Comprovante | None:
        return self.db.scalar(select(Comprovante).where(Comprovante.file_hash == hash_arquivo))

    def criar(self, comprovante: Comprovante) -> Comprovante:
        self.db.add(comprovante)
        self.db.flush()
        self.db.refresh(comprovante)
        return comprovante

    def pegar(self, id_comprovante: int) -> Comprovante | None:
        return self.db.get(Comprovante, id_comprovante)

    def vincular_na_submissao(self, id_submissao: int, id_comprovante: int) -> SubmissaoComprovante:
        vinculo = SubmissaoComprovante(submission_id=id_submissao, evidence_id=id_comprovante)
        self.db.add(vinculo)
        self.db.flush()
        return vinculo

    def pegar_vinculo(self, id_submissao: int, id_comprovante: int) -> SubmissaoComprovante | None:
        consulta = select(SubmissaoComprovante).where(
            SubmissaoComprovante.submission_id == id_submissao,
            SubmissaoComprovante.evidence_id == id_comprovante,
        )
        return self.db.scalar(consulta)

    def remover_vinculo(self, vinculo: SubmissaoComprovante) -> None:
        self.db.delete(vinculo)
        self.db.flush()

    def contar_vinculos(self, id_comprovante: int) -> int:
        consulta = select(SubmissaoComprovante).where(SubmissaoComprovante.evidence_id == id_comprovante)
        return len(list(self.db.scalars(consulta).all()))

    def remover(self, comprovante: Comprovante) -> None:
        self.db.delete(comprovante)
        self.db.flush()

    def get_by_hash(self, file_hash: str) -> Comprovante | None:
        return self.pegar_por_hash(file_hash)

    def create(self, evidence: Comprovante) -> Comprovante:
        return self.criar(evidence)

    def get(self, evidence_id: int) -> Comprovante | None:
        return self.pegar(evidence_id)

    def attach_to_submission(self, submission_id: int, evidence_id: int) -> SubmissaoComprovante:
        return self.vincular_na_submissao(submission_id, evidence_id)

    def get_link(self, submission_id: int, evidence_id: int) -> SubmissaoComprovante | None:
        return self.pegar_vinculo(submission_id, evidence_id)

    def remove_link(self, link: SubmissaoComprovante) -> None:
        self.remover_vinculo(link)

    def count_links(self, evidence_id: int) -> int:
        return self.contar_vinculos(evidence_id)

    def delete(self, evidence: Comprovante) -> None:
        self.remover(evidence)

