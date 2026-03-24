from typing import Optional

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enumeracoes import TipoRegra, UnidadeQuantidade
from app.models.campos_tempo import CamposTempo


class Regra(CamposTempo, Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("activity_categories.id"), nullable=False)
    short_description: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[TipoRegra] = mapped_column(SqlEnum(TipoRegra), nullable=False)
    quantity_unit: Mapped[Optional[UnidadeQuantidade]] = mapped_column(SqlEnum(UnidadeQuantidade))
    minimum_quantity: Mapped[Optional[float]] = mapped_column(Float)
    hours_per_unit: Mapped[Optional[float]] = mapped_column(Float)
    fixed_hours: Mapped[Optional[float]] = mapped_column(Float)
    percentage_multiplier: Mapped[Optional[float]] = mapped_column(Float)
    max_hours_per_item: Mapped[Optional[float]] = mapped_column(Float)
    max_hours_per_category: Mapped[Optional[float]] = mapped_column(Float)
    requires_evidence: Mapped[bool] = mapped_column(default=True, nullable=False)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accepted_mime_types: Mapped[Optional[str]] = mapped_column(String(255))
    documentation_required: Mapped[Optional[str]] = mapped_column(Text)
    special_conditions: Mapped[Optional[str]] = mapped_column(Text)
    source_reference: Mapped[Optional[str]] = mapped_column(String(255))

    category = relationship("CategoriaAtividade", back_populates="rules")

