from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CategoriaAtividade


class RepositorioCategorias:
    def __init__(self, db: Session):
        self.db = db

    def listar_todas(self) -> list[CategoriaAtividade]:
        return list(self.db.scalars(select(CategoriaAtividade).order_by(CategoriaAtividade.name)).all())

    def pegar(self, id_categoria: int) -> CategoriaAtividade | None:
        return self.db.get(CategoriaAtividade, id_categoria)

    def pegar_por_codigo(self, codigo: str) -> CategoriaAtividade | None:
        return self.db.scalar(select(CategoriaAtividade).where(CategoriaAtividade.code == codigo))

    def criar(
        self,
        *,
        codigo: str,
        nome: str,
        horas_maximas: float,
    ) -> CategoriaAtividade:
        categoria = CategoriaAtividade(
            code=codigo,
            name=nome,
            max_hours=horas_maximas,
        )
        self.db.add(categoria)
        self.db.flush()
        return categoria

    def list_all(self) -> list[CategoriaAtividade]:
        return self.listar_todas()

    def get(self, category_id: int) -> CategoriaAtividade | None:
        return self.pegar(category_id)

    def get_by_code(self, code: str) -> CategoriaAtividade | None:
        return self.pegar_por_codigo(code)

    def create(
        self,
        *,
        code: str,
        name: str,
        max_hours: float,
    ) -> CategoriaAtividade:
        return self.criar(
            codigo=code,
            nome=name,
            horas_maximas=max_hours,
        )

