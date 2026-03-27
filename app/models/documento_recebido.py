from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.campos_tempo import CamposTempo


class DocumentoRecebido(CamposTempo, Base):
    __tablename__ = "received_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    submission_id: Mapped[Optional[int]] = mapped_column(ForeignKey("submissions.id"))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    plausibility_status: Mapped[str] = mapped_column(String(30), nullable=False)
    plausibility_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_notes: Mapped[Optional[str]] = mapped_column(Text)
