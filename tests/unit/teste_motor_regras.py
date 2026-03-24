from app.domain.enumeracoes import StatusSubmissao, TipoRegra, UnidadeQuantidade
from app.models import Regra, Submissao
from app.services.motor_regras import MotorDeRegras


class RepositorioFakeSubmissoes:
    def __init__(self, total: float = 0.0):
        self.total = total

    def total_estimated_hours_for_user_category(self, user_id: int, category_id: int, exclude_submission_id: int | None = None) -> float:
        return self.total


def test_regra_por_unidade_respeita_teto_da_categoria():
    repositorio = RepositorioFakeSubmissoes(total=45)
    motor = MotorDeRegras(repositorio)
    regra = Regra(
        id=1,
        category_id=1,
        short_description="Estagio",
        rule_type=TipoRegra.POR_UNIDADE,
        quantity_unit=UnidadeQuantidade.MES,
        minimum_quantity=3,
        hours_per_unit=9,
        max_hours_per_category=54,
        requires_evidence=True,
    )
    submissao = Submissao(id=1, user_id=1, category_id=1, title="Estagio", declared_quantity=3)

    resultado = motor.avaliar(submissao, [regra], quantidade_comprovantes=1)

    assert resultado.status == StatusSubmissao.ESTIMATIVA_APROVADA
    assert resultado.horas_estimadas == 9


def test_regra_por_unidade_rejeita_abaixo_do_minimo():
    repositorio = RepositorioFakeSubmissoes()
    motor = MotorDeRegras(repositorio)
    regra = Regra(
        id=1,
        category_id=1,
        short_description="IC",
        rule_type=TipoRegra.POR_UNIDADE,
        quantity_unit=UnidadeQuantidade.MES,
        minimum_quantity=3,
        hours_per_unit=9,
        max_hours_per_category=54,
        requires_evidence=True,
    )
    submissao = Submissao(id=1, user_id=1, category_id=1, title="IC", declared_quantity=2)

    resultado = motor.avaliar(submissao, [regra], quantidade_comprovantes=1)

    assert resultado.status == StatusSubmissao.ESTIMATIVA_REJEITADA
    assert resultado.horas_estimadas == 0.0


def test_regra_percentual_usa_horas_declaradas():
    repositorio = RepositorioFakeSubmissoes()
    motor = MotorDeRegras(repositorio)
    regra = Regra(
        id=1,
        category_id=1,
        short_description="Curso externo",
        rule_type=TipoRegra.PERCENTUAL_DAS_HORAS,
        quantity_unit=UnidadeQuantidade.CURSO,
        percentage_multiplier=0.5,
        max_hours_per_category=36,
        requires_evidence=True,
    )
    submissao = Submissao(id=1, user_id=1, category_id=1, title="Curso", declared_hours=40)

    resultado = motor.avaliar(submissao, [regra], quantidade_comprovantes=1)

    assert resultado.status == StatusSubmissao.ESTIMATIVA_APROVADA
    assert resultado.horas_estimadas == 20

