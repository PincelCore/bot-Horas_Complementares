from pydantic import BaseModel


class CategoriaLeitura(BaseModel):
    code: str
    name: str
    max_hours: float

    model_config = {"from_attributes": True}

