from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SubmissaoComprovante(Base):
    __tablename__ = "submission_evidences"
    __table_args__ = (UniqueConstraint("submission_id", "evidence_id", name="uq_submission_evidence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), nullable=False)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidences.id"), nullable=False)

    submission = relationship("Submissao", back_populates="evidences")
    evidence = relationship("Comprovante", back_populates="submissions")

