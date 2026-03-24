from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencias import db_session
from app.repositories.repositorio_categorias import RepositorioCategorias
from app.schemas.categoria import CategoriaLeitura

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoriaLeitura])
def listar_categorias(db: Session = Depends(db_session)) -> list[CategoriaLeitura]:
    return RepositorioCategorias(db).listar_todas()

