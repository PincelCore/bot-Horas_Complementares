from app.domain.enumeracoes import StatusSubmissao
from app.services.servico_submissoes import ServicoSubmissoes


def test_transicoes_validas_de_status():
    assert ServicoSubmissoes.validar_transicao_de_status(StatusSubmissao.RASCUNHO, StatusSubmissao.ENVIADA) is True
    assert (
        ServicoSubmissoes.validar_transicao_de_status(
            StatusSubmissao.ENVIADA,
            StatusSubmissao.ESTIMATIVA_APROVADA,
        )
        is True
    )


def test_transicoes_invalidas_de_status():
    assert (
        ServicoSubmissoes.validar_transicao_de_status(
            StatusSubmissao.RASCUNHO,
            StatusSubmissao.ESTIMATIVA_APROVADA,
        )
        is False
    )
    assert (
        ServicoSubmissoes.validar_transicao_de_status(
            StatusSubmissao.ESTIMATIVA_REJEITADA,
            StatusSubmissao.PRECISA_REVISAO,
        )
        is False
    )

