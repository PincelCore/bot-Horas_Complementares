from enum import Enum


class StatusSubmissao(str, Enum):
    DRAFT = "draft"
    RASCUNHO = "draft"
    SUBMITTED = "submitted"
    ENVIADA = "submitted"
    NEEDS_REVIEW = "needs_review"
    PRECISA_REVISAO = "needs_review"
    APPROVED_ESTIMATE = "approved_estimate"
    ESTIMATIVA_APROVADA = "approved_estimate"
    REJECTED_ESTIMATE = "rejected_estimate"
    ESTIMATIVA_REJEITADA = "rejected_estimate"


class TipoRegra(str, Enum):
    PER_UNIT = "per_unit"
    POR_UNIDADE = "per_unit"
    DECLARED_HOURS = "declared_hours"
    HORAS_DECLARADAS = "declared_hours"
    FIXED_HOURS = "fixed_hours"
    HORAS_FIXAS = "fixed_hours"
    PERCENTAGE_OF_DECLARED = "percentage_of_declared"
    PERCENTUAL_DAS_HORAS = "percentage_of_declared"


class UnidadeQuantidade(str, Enum):
    MONTH = "month"
    MES = "month"
    EVENT = "event"
    EVENTO = "event"
    PRESENTATION = "presentation"
    APRESENTACAO = "presentation"
    STAGE = "stage"
    ETAPA = "stage"
    AWARD = "award"
    PREMIACAO = "award"
    DAY = "day"
    DIA = "day"
    SEMESTER = "semester"
    SEMESTRE = "semester"
    COURSE = "course"
    CURSO = "course"


class EstadoBot(str, Enum):
    IDLE = "idle"
    PARADO = "idle"
    AWAITING_CATEGORY = "awaiting_category"
    AGUARDANDO_CATEGORIA = "awaiting_category"
    AGUARDANDO_TITULO = "aguardando_titulo"
    AGUARDANDO_NUMERO = "aguardando_numero"
    AGUARDANDO_COMPROVANTE = "aguardando_comprovante"
    AWAITING_DESCRIPTION = "awaiting_description"
    AWAITING_QUANTITY = "awaiting_quantity"
    AWAITING_DECLARED_HOURS = "awaiting_declared_hours"
    AWAITING_EVIDENCE = "awaiting_evidence"


SubmissionStatus = StatusSubmissao
RuleType = TipoRegra
QuantityUnit = UnidadeQuantidade
BotState = EstadoBot

