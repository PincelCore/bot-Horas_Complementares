from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enumeracoes import StatusSubmissao


class SubmissaoCriacao(BaseModel):
    user_id: int
    category_code: str
    title: str
    description: str | None = None
    declared_quantity: float | None = Field(default=None, ge=0)
    declared_hours: float | None = Field(default=None, ge=0)
    status: StatusSubmissao = StatusSubmissao.ENVIADA


class ComprovanteLeitura(BaseModel):
    id: int
    original_filename: str
    mime_type: str
    file_hash: str
    storage_path: str

    model_config = {"from_attributes": True}


class SubmissaoLeitura(BaseModel):
    id: int
    user_id: int
    category_code: str | None
    category_name: str | None
    rule_id: int | None
    title: str
    description: str | None
    declared_quantity: float | None
    declared_hours: float | None
    estimated_hours: float | None
    status: StatusSubmissao
    review_notes: str | None
    created_at: datetime
    evidences: list[ComprovanteLeitura] = Field(validation_alias="evidence_files")

    model_config = {"from_attributes": True}

