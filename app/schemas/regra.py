from pydantic import BaseModel, Field

from app.domain.enumeracoes import TipoRegra, UnidadeQuantidade
from app.schemas.categoria import CategoriaLeitura


class RegraCriacao(BaseModel):
    category_id: int
    short_description: str
    rule_type: TipoRegra
    quantity_unit: UnidadeQuantidade | None = None
    minimum_quantity: float | None = Field(default=None, ge=0)
    hours_per_unit: float | None = Field(default=None, ge=0)
    fixed_hours: float | None = None
    percentage_multiplier: float | None = None
    max_hours_per_item: float | None = Field(default=None, ge=0)
    max_hours_per_category: float | None = Field(default=None, ge=0)
    requires_evidence: bool = True
    requires_manual_review: bool = False
    accepted_mime_types: str | None = None
    documentation_required: str | None = None
    special_conditions: str | None = None
    source_reference: str | None = None


class RegraLeitura(BaseModel):
    id: int
    short_description: str
    rule_type: TipoRegra
    quantity_unit: UnidadeQuantidade | None
    minimum_quantity: float | None
    hours_per_unit: float | None
    fixed_hours: float | None
    percentage_multiplier: float | None
    max_hours_per_item: float | None
    max_hours_per_category: float | None
    requires_evidence: bool
    requires_manual_review: bool
    accepted_mime_types: str | None
    documentation_required: str | None
    special_conditions: str | None
    source_reference: str | None
    category: CategoriaLeitura

    model_config = {"from_attributes": True}

