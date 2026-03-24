from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Regra


class RepositorioRegras:
    def __init__(self, db: Session):
        self.db = db

    def listar_todas(self) -> list[Regra]:
        consulta = select(Regra).options(joinedload(Regra.category)).order_by(Regra.id)
        return list(self.db.scalars(consulta).unique().all())

    def pegar(self, id_regra: int) -> Regra | None:
        consulta = select(Regra).options(joinedload(Regra.category)).where(Regra.id == id_regra)
        return self.db.scalar(consulta)

    def listar_por_categoria(self, id_categoria: int) -> list[Regra]:
        consulta = select(Regra).options(joinedload(Regra.category)).where(Regra.category_id == id_categoria).order_by(Regra.id)
        return list(self.db.scalars(consulta).unique().all())

    def criar(self, regra: Regra) -> Regra:
        self.db.add(regra)
        self.db.flush()
        self.db.refresh(regra)
        return regra

    def list_all(self) -> list[Regra]:
        return self.listar_todas()

    def get(self, rule_id: int) -> Regra | None:
        return self.pegar(rule_id)

    def get_by_category(self, category_id: int) -> list[Regra]:
        return self.listar_por_categoria(category_id)

    def create(self, rule: Regra) -> Regra:
        return self.criar(rule)

