from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.campos_tempo import CamposTempo


class CategoriaAtividade(CamposTempo, Base):
    __tablename__ = "activity_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_hours: Mapped[float] = mapped_column(Float, nullable=False)

    rules = relationship("Regra", back_populates="category")
    submissions = relationship("Submissao", back_populates="category")
