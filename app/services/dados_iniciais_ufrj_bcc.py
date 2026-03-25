from sqlalchemy.orm import Session

from app.domain.enumeracoes import TipoRegra, UnidadeQuantidade
from app.models import Regra
from app.repositories.repositorio_categorias import RepositorioCategorias
from app.repositories.repositorio_regras import RepositorioRegras

UFRJ_SOURCE = "https://arquivo.ic.ufrj.br/ensino/graduacao/normas-de-atividades-complementares-2"

UFRJ_RULES = [
    {
        "code": "ESTAGIO",
        "name": "Estágio",
        "description": "Regra oficial do BCC/UFRJ: 9h por mês, mínimo de 3 meses, máximo de 54h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 9,
        "max_hours_per_category": 54,
        "documentation_required": "Contratos assinados com vigência e assinaturas do aluno, empregador e Coordenação da CC.",
        "special_conditions": "Somente períodos válidos de estágio durante a graduação.",
    },
    {
        "code": "INICIACAO_CIENTIFICA",
        "name": "Iniciação Científica",
        "description": "Regra oficial do BCC/UFRJ: 9h por mês, mínimo de 3 meses, máximo de 54h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 9,
        "max_hours_per_category": 54,
        "requires_manual_review": True,
        "documentation_required": "Declaração do orientador informando a duração do projeto e certificado de apresentação na SIAC ou JIC.",
        "special_conditions": "A atividade só conta com apresentação na SIAC ou JIC da UFRJ.",
    },
    {
        "code": "OUVINTE_EVENTOS",
        "name": "Ouvinte em Eventos",
        "description": "Regra oficial do BCC/UFRJ: 3h por evento, máximo de 18h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.EVENTO,
        "hours_per_unit": 3,
        "max_hours_per_category": 18,
        "documentation_required": "Certificado de participação ou declaração assinada pela organização do evento.",
        "special_conditions": "Inclui SIAC, JIC, colóquios da computação, seminários, palestras, congressos e simpósios.",
    },
    {
        "code": "APRESENTACAO_EVENTOS",
        "name": "Apresentação de Trabalhos",
        "description": "Regra oficial do BCC/UFRJ: 5h por apresentação, máximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.APRESENTACAO,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "documentation_required": "Certificado de apresentação.",
        "special_conditions": "Inclui SIAC, JIC, Semana da Computação, SNCT, congressos e eventos científicos.",
    },
    {
        "code": "COMPETICOES",
        "name": "Competições Acadêmicas",
        "description": "Regra oficial do BCC/UFRJ: 9h por etapa, máximo de 27h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.ETAPA,
        "hours_per_unit": 9,
        "max_hours_per_category": 27,
        "documentation_required": "Certificado de participação.",
        "special_conditions": "Inclui maratonas de programação e olimpíadas de informática em qualquer etapa.",
    },
    {
        "code": "PREMIACOES",
        "name": "Premiações e Menções Honrosas",
        "description": "Regra oficial do BCC/UFRJ: 5h por premiação, máximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.PREMIACAO,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "documentation_required": "Certificado ou declaração oficial da organização atestando a premiação.",
    },
    {
        "code": "COLEGIADOS",
        "name": "Participação em Colegiados",
        "description": "Regra oficial do BCC/UFRJ: 3h por mês, mínimo de 3 meses, máximo de 36h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 3,
        "max_hours_per_category": 36,
        "documentation_required": "Declaração assinada pelo presidente do colegiado ou congregação com a duração da participação.",
    },
    {
        "code": "COMISSOES",
        "name": "Comissões Acadêmicas",
        "description": "Regra oficial do BCC/UFRJ: 3h por mês, mínimo de 3 meses, máximo de 18h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 3,
        "max_hours_per_category": 18,
        "documentation_required": "Declaração assinada pelo presidente da comissão com a duração da participação.",
    },
    {
        "code": "MESARIO",
        "name": "Mesário em Eleições Oficiais",
        "description": "Regra oficial do BCC/UFRJ: 3h por dia de evento, máximo de 9h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.DIA,
        "hours_per_unit": 3,
        "max_hours_per_category": 9,
        "documentation_required": "Declaração da Justiça Eleitoral.",
    },
    {
        "code": "DIRETORIA_ESTUDANTIL",
        "name": "Diretoria Estudantil",
        "description": "Regra oficial do BCC/UFRJ: 3h por mês, mínimo de 3 meses, máximo de 18h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 3,
        "max_hours_per_category": 18,
        "documentation_required": "Ata oficial do CA ou DCE atestando a eleição e a vigência.",
    },
    {
        "code": "EJCM_MEMBRO",
        "name": "EjCM - Membro Simples",
        "description": "Regra oficial do BCC/UFRJ: 3h por mês, mínimo de 3 meses, máximo de 27h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 3,
        "max_hours_per_category": 27,
        "requires_manual_review": True,
        "documentation_required": "Declaração da EJCM assinada pelo presidente informando cargo e duração.",
        "special_conditions": "Exige CR e CR acumulado acima de 5,0 e ausência de estágio no período.",
    },
    {
        "code": "EJCM_LIDERANCA",
        "name": "EjCM - Conselheiro ou Diretor",
        "description": "Regra oficial do BCC/UFRJ: 5h por mês, mínimo de 3 meses, máximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "requires_manual_review": True,
        "documentation_required": "Declaração da EJCM assinada pelo presidente informando cargo e duração.",
        "special_conditions": "Exige CR e CR acumulado acima de 5,0 e ausência de estágio no período.",
    },
    {
        "code": "ORGANIZACAO_EVENTOS",
        "name": "Organização de Eventos",
        "description": "Regra oficial do BCC/UFRJ: 5h por evento, máximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.EVENTO,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "documentation_required": "Declaração assinada pelo coordenador da organização do evento.",
    },
    {
        "code": "MONITORIA_DISCIPLINA",
        "name": "Monitoria de Disciplina do IC",
        "description": "Regra oficial do BCC/UFRJ: 15h por semestre, máximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.SEMESTRE,
        "hours_per_unit": 15,
        "max_hours_per_category": 30,
        "requires_manual_review": True,
        "documentation_required": "Declaração do professor responsável pela disciplina indicando nome, código e semestre.",
        "special_conditions": "Só conta se não estiver usando os créditos da monitoria no histórico.",
    },
    {
        "code": "MONITORIA_LAB",
        "name": "Monitoria de Laboratório",
        "description": "Regra oficial do BCC/UFRJ: 15h por semestre, máximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.SEMESTRE,
        "hours_per_unit": 15,
        "max_hours_per_category": 30,
        "requires_manual_review": True,
        "documentation_required": "Declaração do professor coordenador ou responsável pelo laboratório indicando o semestre.",
        "special_conditions": "Só conta se não estiver usando os créditos da monitoria no histórico.",
    },
    {
        "code": "TRABALHOS_COMUNITARIOS",
        "name": "Trabalhos Comunitários",
        "description": "Regra oficial do BCC/UFRJ: 5h por mês, mínimo de 3 meses, máximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "documentation_required": "Declaração assinada pelo coordenador da instituição organizadora indicando a duração da participação.",
    },
    {
        "code": "INTERCAMBIO",
        "name": "Intercâmbio Acadêmico",
        "description": "Regra oficial do BCC/UFRJ: 5h por mês, mínimo de 1 mês, máximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 1,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "requires_manual_review": True,
        "documentation_required": "Declaração da universidade de destino indicando a duração do intercâmbio.",
        "special_conditions": "Só conta para atividades não creditadas no histórico.",
    },
    {
        "code": "CURSOS_CC_EXTERNOS",
        "name": "Cursos Externos de Ciência da Computação",
        "description": "Regra oficial do BCC/UFRJ: 50% da carga horária do curso, máximo de 36h.",
        "rule_type": TipoRegra.PERCENTUAL_DAS_HORAS,
        "quantity_unit": UnidadeQuantidade.CURSO,
        "hours_per_unit": 1,
        "percentage_multiplier": 0.5,
        "max_hours_per_category": 36,
        "documentation_required": "Certificado emitido pela instituição organizadora indicando a carga horária total.",
        "special_conditions": "Apenas cursos externos à UFRJ dentro da área de Ciência da Computação e realizados durante a graduação.",
    },
    {
        "code": "CURSOS_IDIOMAS",
        "name": "Cursos de Idiomas",
        "description": "Regra oficial do BCC/UFRJ: 5h por semestre, máximo de 20h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.SEMESTRE,
        "hours_per_unit": 5,
        "max_hours_per_category": 20,
        "documentation_required": "Certificado ou declaração com data de início e término, ou meses/semestres cursados.",
    },
]

def popular_dados_referencia_ufrj_bcc(db: Session) -> None:
    categories = RepositorioCategorias(db)
    rules = RepositorioRegras(db)

    for item in UFRJ_RULES:
        category = categories.get_by_code(item["code"])
        if not category:
            category = categories.create(
                code=item["code"],
                name=item["name"],
                max_hours=item["max_hours_per_category"],
            )
        else:
            category.name = item["name"]
            category.max_hours = item["max_hours_per_category"]

        existing_rules = rules.get_by_category(category.id)
        payload = {
            "category_id": category.id,
            "short_description": item["description"],
            "rule_type": item["rule_type"],
            "quantity_unit": item.get("quantity_unit"),
            "minimum_quantity": item.get("minimum_quantity"),
            "hours_per_unit": item.get("hours_per_unit"),
            "fixed_hours": item.get("fixed_hours"),
            "percentage_multiplier": item.get("percentage_multiplier"),
            "max_hours_per_item": item.get("max_hours_per_item"),
            "max_hours_per_category": item.get("max_hours_per_category"),
            "requires_evidence": True,
            "requires_manual_review": item.get("requires_manual_review", False),
            "accepted_mime_types": "application/pdf,image/jpeg,image/png",
            "documentation_required": item.get("documentation_required"),
            "special_conditions": item.get("special_conditions"),
            "source_reference": UFRJ_SOURCE,
        }

        if existing_rules:
            rule = existing_rules[0]
            for key, value in payload.items():
                setattr(rule, key, value)
        else:
            db.add(Regra(**payload))

    db.commit()


seed_ufrj_bcc_reference_data = popular_dados_referencia_ufrj_bcc

