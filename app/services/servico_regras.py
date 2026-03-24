from sqlalchemy.orm import Session

from app.models import Regra
from app.repositories.repositorio_regras import RepositorioRegras


class ServicoRegras:
    def __init__(self, db: Session):
        self.repositorio_regras = RepositorioRegras(db)

    def listar_regras(self) -> list[Regra]:
        return self.repositorio_regras.list_all()

    def list_rules(self) -> list[Regra]:
        return self.listar_regras()


RuleService = ServicoRegras

