from typing import Optional

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enumeracoes import StatusSubmissao
from app.models.campos_tempo import CamposTempo


class Submissao(CamposTempo, Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("activity_categories.id"))
    rule_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rules.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    declared_quantity: Mapped[Optional[float]] = mapped_column(Float)
    declared_hours: Mapped[Optional[float]] = mapped_column(Float)
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[StatusSubmissao] = mapped_column(
        SqlEnum(StatusSubmissao),
        default=StatusSubmissao.RASCUNHO,
        nullable=False,
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text)

    user = relationship("Usuario", back_populates="submissions")
    category = relationship("CategoriaAtividade", back_populates="submissions")
    evidences = relationship("SubmissaoComprovante", back_populates="submission", cascade="all, delete-orphan")

    @property
    def evidence_files(self):
        return [item.evidence for item in self.evidences]

    @property
    def category_code(self) -> str | None:
        return self.category.code if self.category else None

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None

