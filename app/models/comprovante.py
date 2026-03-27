from typing import Optional

from sqlalchemy import ForeignKey, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.campos_tempo import CamposTempo


class Comprovante(CamposTempo, Base):
    __tablename__ = "evidences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_content: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    source_document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("received_documents.id"))

    submissions = relationship("SubmissaoComprovante", back_populates="evidence", cascade="all, delete-orphan")

