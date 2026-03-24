from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Usuario


class RepositorioUsuarios:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.flush()
        self.db.refresh(usuario)
        return usuario

    def pegar(self, id_usuario: int) -> Usuario | None:
        return self.db.get(Usuario, id_usuario)

    def pegar_por_chat_id_telegram(self, chat_id_telegram: int) -> Usuario | None:
        return self.db.scalar(select(Usuario).where(Usuario.telegram_chat_id == chat_id_telegram))

    def create(self, user: Usuario) -> Usuario:
        return self.criar(user)

    def get(self, user_id: int) -> Usuario | None:
        return self.pegar(user_id)

    def get_by_telegram_chat_id(self, telegram_chat_id: int) -> Usuario | None:
        return self.pegar_por_chat_id_telegram(telegram_chat_id)

