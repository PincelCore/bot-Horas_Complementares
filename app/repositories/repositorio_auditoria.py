from sqlalchemy.orm import Session

from app.models import EventoAuditoria


class RepositorioAuditoria:
    def __init__(self, db: Session):
        self.db = db

    def registrar(self, tipo_evento: str, mensagem: str, id_submissao: int | None = None) -> EventoAuditoria:
        evento = EventoAuditoria(
            submission_id=id_submissao,
            event_type=tipo_evento,
            message=mensagem,
        )
        self.db.add(evento)
        self.db.flush()
        self.db.refresh(evento)
        return evento

    def log(self, event_type: str, message: str, submission_id: int | None = None) -> EventoAuditoria:
        return self.registrar(event_type, message, submission_id)
