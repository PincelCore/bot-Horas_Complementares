from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.domain.enumeracoes import StatusSubmissao
from app.models import Comprovante, Submissao
from app.repositories.repositorio_auditoria import RepositorioAuditoria
from app.repositories.repositorio_categorias import RepositorioCategorias
from app.repositories.repositorio_comprovantes import RepositorioComprovantes
from app.repositories.repositorio_regras import RepositorioRegras
from app.repositories.repositorio_submissoes import RepositorioSubmissoes
from app.repositories.repositorio_usuarios import RepositorioUsuarios
from app.schemas.submissao import SubmissaoCriacao
from app.services.excecoes import ErroDominio
from app.services.armazenamento_arquivos import ServicoArquivos
from app.services.motor_regras import MotorDeRegras


class ServicoSubmissoes:
    def __init__(self, db: Session):
        self.db = db
        self.repositorio_usuarios = RepositorioUsuarios(db)
        self.repositorio_categorias = RepositorioCategorias(db)
        self.repositorio_regras = RepositorioRegras(db)
        self.repositorio_submissoes = RepositorioSubmissoes(db)
        self.repositorio_comprovantes = RepositorioComprovantes(db)
        self.repositorio_auditoria = RepositorioAuditoria(db)
        self.servico_arquivos = ServicoArquivos()
        self.motor_regras = MotorDeRegras(self.repositorio_submissoes)

    def criar_submissao(self, dados: SubmissaoCriacao) -> Submissao:
        usuario = self.repositorio_usuarios.pegar(dados.user_id)
        if not usuario:
            raise ErroDominio("Usuario nao encontrado.")

        categoria = self.repositorio_categorias.pegar_por_codigo(dados.category_code)
        if not categoria:
            raise ErroDominio("Categoria nao encontrada.")

        submissao = Submissao(
            user_id=dados.user_id,
            category_id=categoria.id,
            title=dados.title,
            description=dados.description,
            declared_quantity=dados.declared_quantity,
            declared_hours=dados.declared_hours,
            status=dados.status,
        )
        self.repositorio_submissoes.criar(submissao)
        self.repositorio_auditoria.registrar("submissao.criada", f"Submissao {submissao.id} criada.", submissao.id)
        if submissao.status != StatusSubmissao.RASCUNHO:
            self._avaliar_submissao(submissao)
        self.db.commit()
        return self.repositorio_submissoes.pegar(submissao.id)

    def create_submission(self, payload: SubmissaoCriacao) -> Submissao:
        return self.criar_submissao(payload)

    def adicionar_comprovante(self, submissao_id: int, arquivo: UploadFile) -> Submissao:
        submissao = self.repositorio_submissoes.pegar(submissao_id)
        if not submissao:
            raise ErroDominio("Submissao nao encontrada.")

        arquivo_preparado = self.servico_arquivos.salvar(arquivo)
        comprovante_existente = self.repositorio_comprovantes.pegar_por_hash(arquivo_preparado.hash_arquivo)
        if comprovante_existente:
            if not comprovante_existente.file_content:
                comprovante_existente.file_content = arquivo_preparado.conteudo
                comprovante_existente.storage_path = arquivo_preparado.caminho_storage
                comprovante_existente.stored_filename = arquivo_preparado.nome_interno
            comprovante = comprovante_existente
        else:
            comprovante = Comprovante(
                user_id=submissao.user_id,
                original_filename=arquivo.filename or arquivo_preparado.nome_interno,
                stored_filename=arquivo_preparado.nome_interno,
                mime_type=arquivo.content_type or "application/octet-stream",
                file_hash=arquivo_preparado.hash_arquivo,
                storage_path=arquivo_preparado.caminho_storage,
                file_content=arquivo_preparado.conteudo,
            )
            self.repositorio_comprovantes.criar(comprovante)

        comprovantes_ja_vinculados = {item.evidence_id for item in submissao.evidences}
        if comprovante.id not in comprovantes_ja_vinculados:
            self.repositorio_comprovantes.vincular_na_submissao(submissao.id, comprovante.id)

        self.repositorio_auditoria.registrar(
            "submissao.comprovante_adicionado",
            f"Comprovante {comprovante.id} vinculado a submissao {submissao.id}.",
            submissao.id,
        )

        self.db.flush()
        self.db.expire_all()
        submissao_atualizada = self.repositorio_submissoes.pegar(submissao.id)
        self._avaliar_submissao(submissao_atualizada)
        self.db.commit()
        return self.repositorio_submissoes.pegar(submissao.id)

    def add_evidence(self, submission_id: int, upload_file: UploadFile) -> Submissao:
        return self.adicionar_comprovante(submission_id, upload_file)

    def adicionar_comprovante_por_bytes(
        self,
        submissao_id: int,
        *,
        nome_arquivo: str,
        tipo_mime: str,
        conteudo: bytes,
    ) -> Submissao:
        arquivo = self.servico_arquivos.criar_upload_file(nome_arquivo=nome_arquivo, tipo_mime=tipo_mime, conteudo=conteudo)
        return self.adicionar_comprovante(submissao_id, arquivo)

    def add_evidence_from_bytes(
        self,
        submission_id: int,
        *,
        filename: str,
        mime_type: str,
        content: bytes,
    ) -> Submissao:
        return self.adicionar_comprovante_por_bytes(
            submission_id,
            nome_arquivo=filename,
            tipo_mime=mime_type,
            conteudo=content,
        )

    def remover_comprovante(self, submissao_id: int, comprovante_id: int) -> Submissao:
        submissao = self.repositorio_submissoes.pegar(submissao_id)
        if not submissao:
            raise ErroDominio("Submissao nao encontrada.")

        vinculo = self.repositorio_comprovantes.pegar_vinculo(submissao_id, comprovante_id)
        if not vinculo:
            raise ErroDominio("Comprovante nao encontrado nessa submissao.")

        comprovante = self.repositorio_comprovantes.pegar(comprovante_id)
        self.repositorio_comprovantes.remover_vinculo(vinculo)
        if comprovante and self.repositorio_comprovantes.contar_vinculos(comprovante_id) == 0:
            self.repositorio_comprovantes.remover(comprovante)

        self.repositorio_auditoria.registrar(
            "submissao.comprovante_removido",
            f"Comprovante {comprovante_id} removido da submissao {submissao_id}.",
            submissao_id,
        )
        self.db.flush()
        self.db.expire_all()
        submissao_atualizada = self.repositorio_submissoes.pegar(submissao_id)
        self._avaliar_submissao(submissao_atualizada)
        self.db.commit()
        return self.repositorio_submissoes.pegar(submissao_id)

    def remove_evidence(self, submission_id: int, evidence_id: int) -> Submissao:
        return self.remover_comprovante(submission_id, evidence_id)

    def listar_comprovantes_da_submissao(self, submissao_id: int) -> list[Comprovante]:
        submissao = self.repositorio_submissoes.pegar(submissao_id)
        if not submissao:
            raise ErroDominio("Submissao nao encontrada.")
        return submissao.evidence_files

    def list_submission_evidences(self, submission_id: int) -> list[Comprovante]:
        return self.listar_comprovantes_da_submissao(submission_id)

    def pegar_submissao(self, submissao_id: int) -> Submissao | None:
        return self.repositorio_submissoes.pegar(submissao_id)

    def get_submission(self, submission_id: int) -> Submissao | None:
        return self.pegar_submissao(submission_id)

    def listar_submissoes_do_usuario(self, user_id: int) -> list[Submissao]:
        return self.repositorio_submissoes.listar_por_usuario(user_id)

    def list_user_submissions(self, user_id: int) -> list[Submissao]:
        return self.listar_submissoes_do_usuario(user_id)

    def avaliar_submissao(self, submissao_id: int) -> Submissao:
        submissao = self.repositorio_submissoes.pegar(submissao_id)
        if not submissao:
            raise ErroDominio("Submissao nao encontrada.")
        self._avaliar_submissao(submissao)
        self.db.commit()
        return self.repositorio_submissoes.pegar(submissao_id)

    def evaluate_submission(self, submission_id: int) -> Submissao:
        return self.avaliar_submissao(submission_id)

    def _avaliar_submissao(self, submissao: Submissao) -> None:
        if submissao.category_id is None:
            raise ErroDominio("Categoria e obrigatoria.")

        regras = self.repositorio_regras.listar_por_categoria(submissao.category_id)
        resultado = self.motor_regras.avaliar(submissao, regras, len(submissao.evidences))
        if len(regras) == 1:
            submissao.rule_id = regras[0].id
        submissao.estimated_hours = resultado.horas_estimadas
        submissao.status = resultado.status
        submissao.review_notes = resultado.observacoes
        self.repositorio_auditoria.registrar("submissao.avaliada", resultado.observacoes or "Submissao avaliada.", submissao.id)

    @staticmethod
    def validar_transicao_de_status(atual: StatusSubmissao, novo: StatusSubmissao) -> bool:
        transicoes_permitidas = {
            StatusSubmissao.RASCUNHO: {StatusSubmissao.ENVIADA},
            StatusSubmissao.ENVIADA: {
                StatusSubmissao.PRECISA_REVISAO,
                StatusSubmissao.ESTIMATIVA_APROVADA,
                StatusSubmissao.ESTIMATIVA_REJEITADA,
            },
            StatusSubmissao.PRECISA_REVISAO: {
                StatusSubmissao.ESTIMATIVA_APROVADA,
                StatusSubmissao.ESTIMATIVA_REJEITADA,
            },
            StatusSubmissao.ESTIMATIVA_APROVADA: set(),
            StatusSubmissao.ESTIMATIVA_REJEITADA: set(),
        }
        return novo in transicoes_permitidas[atual]

    @staticmethod
    def validate_status_transition(current: StatusSubmissao, new: StatusSubmissao) -> bool:
        return ServicoSubmissoes.validar_transicao_de_status(current, new)


SubmissionService = ServicoSubmissoes

