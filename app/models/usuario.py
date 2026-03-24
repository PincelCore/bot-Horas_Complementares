from typing import Optional

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enumeracoes import EstadoBot
from app.models.campos_tempo import CamposTempo


class Usuario(CamposTempo, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(255))
    bot_state: Mapped[str] = mapped_column(String(50), default=EstadoBot.PARADO.value, nullable=False)
    active_submission_id: Mapped[Optional[int]] = mapped_column(nullable=True)

    submissions = relationship("Submissao", back_populates="user")

