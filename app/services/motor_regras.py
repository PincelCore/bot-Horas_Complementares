from app.domain.enumeracoes import StatusSubmissao, TipoRegra
from app.models import Regra, Submissao
from app.repositories.repositorio_submissoes import RepositorioSubmissoes


class ResultadoAvaliacaoRegra:
    def __init__(self, horas_estimadas: float | None, status: StatusSubmissao, observacoes: str | None = None):
        self.horas_estimadas = horas_estimadas
        self.status = status
        self.observacoes = observacoes

    @property
    def estimated_hours(self) -> float | None:
        return self.horas_estimadas

    @property
    def notes(self) -> str | None:
        return self.observacoes


class MotorDeRegras:
    def __init__(self, repositorio_submissoes: RepositorioSubmissoes):
        self.repositorio_submissoes = repositorio_submissoes

    def avaliar(self, submissao: Submissao, regras: list[Regra], quantidade_comprovantes: int) -> ResultadoAvaliacaoRegra:
        if not regras:
            return ResultadoAvaliacaoRegra(None, StatusSubmissao.PRECISA_REVISAO, "Nenhuma regra cadastrada para a categoria.")
        if len(regras) > 1:
            return ResultadoAvaliacaoRegra(None, StatusSubmissao.PRECISA_REVISAO, "Mais de uma regra encontrada para a categoria.")

        regra = regras[0]
        if regra.requires_evidence and quantidade_comprovantes == 0:
            return ResultadoAvaliacaoRegra(None, StatusSubmissao.PRECISA_REVISAO, "A categoria exige comprovante.")
        if regra.rule_type == TipoRegra.POR_UNIDADE:
            if submissao.declared_quantity is None:
                return ResultadoAvaliacaoRegra(None, StatusSubmissao.PRECISA_REVISAO, "Quantidade da atividade ausente para calculo.")
            if regra.minimum_quantity is not None and submissao.declared_quantity < regra.minimum_quantity:
                return ResultadoAvaliacaoRegra(
                    0.0,
                    StatusSubmissao.ESTIMATIVA_REJEITADA,
                    f"Atividade abaixo do minimo exigido ({regra.minimum_quantity:g} {self._rotulo_unidade(regra)}).",
                )
        if regra.rule_type == TipoRegra.PERCENTUAL_DAS_HORAS and submissao.declared_hours is None:
            return ResultadoAvaliacaoRegra(None, StatusSubmissao.PRECISA_REVISAO, "Carga horaria base ausente para calculo.")
        if submissao.declared_hours is None and regra.rule_type == TipoRegra.HORAS_DECLARADAS:
            return ResultadoAvaliacaoRegra(None, StatusSubmissao.PRECISA_REVISAO, "Horas declaradas ausentes para calculo.")

        horas_estimadas = self._calcular(regra, submissao.declared_quantity, submissao.declared_hours)
        if regra.max_hours_per_item is not None:
            horas_estimadas = min(horas_estimadas, regra.max_hours_per_item)

        horas_ja_alocadas = self.repositorio_submissoes.total_estimated_hours_for_user_category(
            submissao.user_id,
            submissao.category_id,
            exclude_submission_id=submissao.id,
        )
        if regra.max_hours_per_category is not None:
            horas_restantes = max(regra.max_hours_per_category - horas_ja_alocadas, 0.0)
            horas_estimadas = min(horas_estimadas, horas_restantes)

        if horas_estimadas <= 0:
            return ResultadoAvaliacaoRegra(
                0.0,
                StatusSubmissao.ESTIMATIVA_REJEITADA,
                "Sem horas restantes disponiveis para a categoria.",
            )

        observacoes = ["Estimativa calculada com sucesso."]
        if regra.minimum_quantity is not None and regra.rule_type == TipoRegra.POR_UNIDADE:
            observacoes.append(f"Minimo oficial considerado: {regra.minimum_quantity:g} {self._rotulo_unidade(regra)}.")
        if regra.special_conditions:
            observacoes.append(f"Conferir condicoes oficiais: {regra.special_conditions}")
        if regra.documentation_required:
            observacoes.append(f"Documentacao esperada: {regra.documentation_required}")
        if regra.requires_manual_review:
            observacoes.append("Esta categoria depende de conferencia manual adicional pela regra oficial.")
        return ResultadoAvaliacaoRegra(horas_estimadas, StatusSubmissao.ESTIMATIVA_APROVADA, " ".join(observacoes))

    def evaluate(self, submission: Submissao, rules: list[Regra], evidence_count: int) -> ResultadoAvaliacaoRegra:
        return self.avaliar(submission, rules, evidence_count)

    @staticmethod
    def _calcular(regra: Regra, quantidade_declarada: float | None, horas_declaradas: float | None) -> float:
        if regra.rule_type == TipoRegra.POR_UNIDADE:
            return float((quantidade_declarada or 0.0) * (regra.hours_per_unit or 0.0))
        if regra.rule_type == TipoRegra.HORAS_FIXAS:
            return float(regra.fixed_hours or 0.0)
        if regra.rule_type == TipoRegra.PERCENTUAL_DAS_HORAS:
            return float((horas_declaradas or 0.0) * (regra.percentage_multiplier or 0.0))
        return float(horas_declaradas or 0.0)

    @classmethod
    def _unit_label(cls, regra: Regra) -> str:
        return cls._rotulo_unidade(regra)

    @staticmethod
    def _rotulo_unidade(regra: Regra) -> str:
        if regra.quantity_unit is None:
            return "unidades"
        return {
            "month": "mes(es)",
            "event": "evento(s)",
            "presentation": "apresentacao(oes)",
            "stage": "etapa(s)",
            "award": "premiacao(oes)",
            "day": "dia(s)",
            "semester": "semestre(s)",
            "course": "curso(s)",
        }.get(regra.quantity_unit.value, "unidades")


RuleEvaluationResult = ResultadoAvaliacaoRegra
RuleEngine = MotorDeRegras

