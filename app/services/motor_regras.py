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
        observacoes: list[str] = []
        if regra.requires_evidence and quantidade_comprovantes == 0:
            return ResultadoAvaliacaoRegra(None, StatusSubmissao.PRECISA_REVISAO, "A categoria exige comprovante.")
        if regra.rule_type == TipoRegra.POR_UNIDADE:
            if submissao.declared_quantity is None:
                return ResultadoAvaliacaoRegra(None, StatusSubmissao.PRECISA_REVISAO, "Quantidade da atividade ausente para cálculo.")
            if regra.minimum_quantity is not None and submissao.declared_quantity < regra.minimum_quantity:
                return ResultadoAvaliacaoRegra(
                    0.0,
                    StatusSubmissao.ESTIMATIVA_REJEITADA,
                    f"Atividade abaixo do mínimo exigido ({regra.minimum_quantity:g} {self._rotulo_unidade(regra)}).",
                )
        if regra.rule_type == TipoRegra.PERCENTUAL_DAS_HORAS and submissao.declared_hours is None:
            return ResultadoAvaliacaoRegra(None, StatusSubmissao.PRECISA_REVISAO, "Carga horária base ausente para cálculo.")
        if submissao.declared_hours is None and regra.rule_type == TipoRegra.HORAS_DECLARADAS:
            return ResultadoAvaliacaoRegra(None, StatusSubmissao.PRECISA_REVISAO, "Horas declaradas ausentes para cálculo.")

        horas_brutas = self._calcular(regra, submissao.declared_quantity, submissao.declared_hours)
        horas_estimadas = horas_brutas
        if regra.max_hours_per_item is not None:
            if horas_estimadas > regra.max_hours_per_item:
                observacoes.append(
                    f"A conta inicial deu {self._formatar_horas(horas_estimadas)}, mas cada lançamento dessa categoria vai até "
                    f"{self._formatar_horas(regra.max_hours_per_item)}."
                )
            horas_estimadas = min(horas_estimadas, regra.max_hours_per_item)

        horas_ja_alocadas = self.repositorio_submissoes.total_estimated_hours_for_user_category(
            submissao.user_id,
            submissao.category_id,
            exclude_submission_id=submissao.id,
        )
        if regra.max_hours_per_category is not None:
            horas_restantes = max(regra.max_hours_per_category - horas_ja_alocadas, 0.0)
            if horas_estimadas > horas_restantes:
                if horas_ja_alocadas > 0:
                    observacoes.append(
                        f"A conta inicial deu {self._formatar_horas(horas_estimadas)}, mas você já tinha "
                        f"{self._formatar_horas(horas_ja_alocadas)} nessa categoria e sobravam só "
                        f"{self._formatar_horas(horas_restantes)} do teto oficial de {self._formatar_horas(regra.max_hours_per_category)}."
                    )
                else:
                    observacoes.append(
                        f"A conta inicial deu {self._formatar_horas(horas_estimadas)}, mas o teto oficial dessa categoria é "
                        f"{self._formatar_horas(regra.max_hours_per_category)}."
                    )
            horas_estimadas = min(horas_estimadas, horas_restantes)

        if horas_estimadas <= 0:
            return ResultadoAvaliacaoRegra(
                0.0,
                StatusSubmissao.ESTIMATIVA_REJEITADA,
                "Sem horas restantes disponíveis para a categoria.",
            )

        observacoes.insert(0, "Estimativa calculada com sucesso.")
        if regra.minimum_quantity is not None and regra.rule_type == TipoRegra.POR_UNIDADE:
            observacoes.append(f"Mínimo oficial considerado: {regra.minimum_quantity:g} {self._rotulo_unidade(regra)}.")
        if regra.special_conditions:
            observacoes.append(f"Conferir condições oficiais: {regra.special_conditions}")
        if regra.documentation_required:
            observacoes.append(f"Documentação esperada: {regra.documentation_required}")
        if regra.requires_manual_review:
            observacoes.append("Esta categoria depende de conferência manual adicional pela regra oficial.")
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
            "month": "mês(es)",
            "event": "evento(s)",
            "presentation": "apresentação(ões)",
            "stage": "etapa(s)",
            "award": "premiação(ões)",
            "day": "dia(s)",
            "semester": "semestre(s)",
            "course": "curso(s)",
        }.get(regra.quantity_unit.value, "unidades")

    @staticmethod
    def _formatar_horas(valor: float | None) -> str:
        if valor is None:
            return "0h"
        return f"{valor:.2f}h".replace(".", ",")


RuleEvaluationResult = ResultadoAvaliacaoRegra
RuleEngine = MotorDeRegras

