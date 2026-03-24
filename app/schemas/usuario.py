from pydantic import BaseModel, EmailStr


class UsuarioCriacao(BaseModel):
    full_name: str
    email: EmailStr | None = None
    telegram_chat_id: int | None = None
    telegram_username: str | None = None


class UsuarioLeitura(BaseModel):
    id: int
    full_name: str
    email: str | None
    telegram_chat_id: int | None
    telegram_username: str | None

    model_config = {"from_attributes": True}


class ResumoHorasCategoria(BaseModel):
    category_code: str | None
    category_name: str
    total_hours: float


class ContagemStatus(BaseModel):
    status: str
    count: int


class ResumoUsuario(BaseModel):
    user_id: int
    total_estimated_hours: float
    required_hours: float
    remaining_hours: float
    categories: list[ResumoHorasCategoria]
    statuses: list[ContagemStatus]

