from sqlalchemy.orm import Session

from app.domain.enumeracoes import TipoRegra, UnidadeQuantidade
from app.models import Regra
from app.repositories.repositorio_categorias import RepositorioCategorias
from app.repositories.repositorio_regras import RepositorioRegras

UFRJ_SOURCE = "https://arquivo.ic.ufrj.br/ensino/graduacao/normas-de-atividades-complementares-2"

UFRJ_RULES = [
    {
        "code": "ESTAGIO",
        "name": "Estagio",
        "description": "Regra oficial do BCC/UFRJ: 9h por mes, minimo de 3 meses, maximo de 54h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 9,
        "max_hours_per_category": 54,
        "documentation_required": "Contratos assinados com vigencia e assinaturas do aluno, empregador e Coordenacao da CC.",
        "special_conditions": "Somente periodos validos de estagio durante a graduacao.",
    },
    {
        "code": "INICIACAO_CIENTIFICA",
        "name": "Iniciacao Cientifica",
        "description": "Regra oficial do BCC/UFRJ: 9h por mes, minimo de 3 meses, maximo de 54h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 9,
        "max_hours_per_category": 54,
        "requires_manual_review": True,
        "documentation_required": "Declaracao do orientador informando a duracao do projeto e certificado de apresentacao na SIAC ou JIC.",
        "special_conditions": "A atividade so conta com apresentacao na SIAC ou JIC da UFRJ.",
    },
    {
        "code": "OUVINTE_EVENTOS",
        "name": "Ouvinte em Eventos",
        "description": "Regra oficial do BCC/UFRJ: 3h por evento, maximo de 18h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.EVENTO,
        "hours_per_unit": 3,
        "max_hours_per_category": 18,
        "documentation_required": "Certificado de participacao ou declaracao assinada pela organizacao do evento.",
        "special_conditions": "Inclui SIAC, JIC, coloquios da computacao, seminarios, palestras, congressos e simposios.",
    },
    {
        "code": "APRESENTACAO_EVENTOS",
        "name": "Apresentacao de Trabalhos",
        "description": "Regra oficial do BCC/UFRJ: 5h por apresentacao, maximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.APRESENTACAO,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "documentation_required": "Certificado de apresentacao.",
        "special_conditions": "Inclui SIAC, JIC, Semana da Computacao, SNCT, congressos e eventos cientificos.",
    },
    {
        "code": "COMPETICOES",
        "name": "Competicoes Academicas",
        "description": "Regra oficial do BCC/UFRJ: 9h por etapa, maximo de 27h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.ETAPA,
        "hours_per_unit": 9,
        "max_hours_per_category": 27,
        "documentation_required": "Certificado de participacao.",
        "special_conditions": "Inclui maratonas de programacao e olimpiadas de informatica em qualquer etapa.",
    },
    {
        "code": "PREMIACOES",
        "name": "Premiacoes e Mencoes Honrosas",
        "description": "Regra oficial do BCC/UFRJ: 5h por premiacao, maximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.PREMIACAO,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "documentation_required": "Certificado ou declaracao oficial da organizacao atestando a premiacao.",
    },
    {
        "code": "COLEGIADOS",
        "name": "Participacao em Colegiados",
        "description": "Regra oficial do BCC/UFRJ: 3h por mes, minimo de 3 meses, maximo de 36h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 3,
        "max_hours_per_category": 36,
        "documentation_required": "Declaracao assinada pelo presidente do colegiado ou congregacao com a duracao da participacao.",
    },
    {
        "code": "COMISSOES",
        "name": "Comissoes Academicas",
        "description": "Regra oficial do BCC/UFRJ: 3h por mes, minimo de 3 meses, maximo de 18h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 3,
        "max_hours_per_category": 18,
        "documentation_required": "Declaracao assinada pelo presidente da comissao com a duracao da participacao.",
    },
    {
        "code": "MESARIO",
        "name": "Mesario em Eleicoes Oficiais",
        "description": "Regra oficial do BCC/UFRJ: 3h por dia de evento, maximo de 9h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.DIA,
        "hours_per_unit": 3,
        "max_hours_per_category": 9,
        "documentation_required": "Declaracao da Justica Eleitoral.",
    },
    {
        "code": "DIRETORIA_ESTUDANTIL",
        "name": "Diretoria Estudantil",
        "description": "Regra oficial do BCC/UFRJ: 3h por mes, minimo de 3 meses, maximo de 18h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 3,
        "max_hours_per_category": 18,
        "documentation_required": "Ata oficial do CA ou DCE atestando a eleicao e a vigencia.",
    },
    {
        "code": "EJCM_MEMBRO",
        "name": "EjCM - Membro Simples",
        "description": "Regra oficial do BCC/UFRJ: 3h por mes, minimo de 3 meses, maximo de 27h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 3,
        "max_hours_per_category": 27,
        "requires_manual_review": True,
        "documentation_required": "Declaracao da EJCM assinada pelo presidente informando cargo e duracao.",
        "special_conditions": "Exige CR e CR acumulado acima de 5,0 e ausencia de estagio no periodo.",
    },
    {
        "code": "EJCM_LIDERANCA",
        "name": "EjCM - Conselheiro ou Diretor",
        "description": "Regra oficial do BCC/UFRJ: 5h por mes, minimo de 3 meses, maximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "requires_manual_review": True,
        "documentation_required": "Declaracao da EJCM assinada pelo presidente informando cargo e duracao.",
        "special_conditions": "Exige CR e CR acumulado acima de 5,0 e ausencia de estagio no periodo.",
    },
    {
        "code": "ORGANIZACAO_EVENTOS",
        "name": "Organizacao de Eventos",
        "description": "Regra oficial do BCC/UFRJ: 5h por evento, maximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.EVENTO,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "documentation_required": "Declaracao assinada pelo coordenador da organizacao do evento.",
    },
    {
        "code": "MONITORIA_DISCIPLINA",
        "name": "Monitoria de Disciplina do IC",
        "description": "Regra oficial do BCC/UFRJ: 15h por semestre, maximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.SEMESTRE,
        "hours_per_unit": 15,
        "max_hours_per_category": 30,
        "requires_manual_review": True,
        "documentation_required": "Declaracao do professor responsavel pela disciplina indicando nome, codigo e semestre.",
        "special_conditions": "So conta se nao estiver usando os creditos da monitoria no historico.",
    },
    {
        "code": "MONITORIA_LAB",
        "name": "Monitoria de Laboratorio",
        "description": "Regra oficial do BCC/UFRJ: 15h por semestre, maximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.SEMESTRE,
        "hours_per_unit": 15,
        "max_hours_per_category": 30,
        "requires_manual_review": True,
        "documentation_required": "Declaracao do professor coordenador ou responsavel pelo laboratorio indicando o semestre.",
        "special_conditions": "So conta se nao estiver usando os creditos da monitoria no historico.",
    },
    {
        "code": "TRABALHOS_COMUNITARIOS",
        "name": "Trabalhos Comunitarios",
        "description": "Regra oficial do BCC/UFRJ: 5h por mes, minimo de 3 meses, maximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 3,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "documentation_required": "Declaracao assinada pelo coordenador da instituicao organizadora indicando a duracao da participacao.",
    },
    {
        "code": "INTERCAMBIO",
        "name": "Intercambio Academico",
        "description": "Regra oficial do BCC/UFRJ: 5h por mes, minimo de 1 mes, maximo de 30h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.MES,
        "minimum_quantity": 1,
        "hours_per_unit": 5,
        "max_hours_per_category": 30,
        "requires_manual_review": True,
        "documentation_required": "Declaracao da universidade de destino indicando a duracao do intercambio.",
        "special_conditions": "So conta para atividades nao creditadas no historico.",
    },
    {
        "code": "CURSOS_CC_EXTERNOS",
        "name": "Cursos Externos de Ciencia da Computacao",
        "description": "Regra oficial do BCC/UFRJ: 50% da carga horaria do curso, maximo de 36h.",
        "rule_type": TipoRegra.PERCENTUAL_DAS_HORAS,
        "quantity_unit": UnidadeQuantidade.CURSO,
        "hours_per_unit": 1,
        "percentage_multiplier": 0.5,
        "max_hours_per_category": 36,
        "documentation_required": "Certificado emitido pela instituicao organizadora indicando a carga horaria total.",
        "special_conditions": "Apenas cursos externos a UFRJ dentro da area de Ciencia da Computacao e realizados durante a graduacao.",
    },
    {
        "code": "CURSOS_IDIOMAS",
        "name": "Cursos de Idiomas",
        "description": "Regra oficial do BCC/UFRJ: 5h por semestre, maximo de 20h.",
        "rule_type": TipoRegra.POR_UNIDADE,
        "quantity_unit": UnidadeQuantidade.SEMESTRE,
        "hours_per_unit": 5,
        "max_hours_per_category": 20,
        "documentation_required": "Certificado ou declaracao com data de inicio e termino, ou meses/semestres cursados.",
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

