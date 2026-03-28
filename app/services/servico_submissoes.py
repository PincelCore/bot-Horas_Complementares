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
from app.services.servico_documentos_recebidos import ServicoDocumentosRecebidos
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
        self.servico_documentos = ServicoDocumentosRecebidos(db)
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

        if len(submissao.evidence_files) >= self.servico_arquivos.configuracoes.max_evidences_per_submission:
            raise ErroDominio("Essa atividade ja atingiu o limite de comprovantes permitidos.")

        usuario = self.repositorio_usuarios.pegar(submissao.user_id)
        if not usuario:
            raise ErroDominio("Usuario nao encontrado.")

        conteudo = arquivo.file.read()
        documento, validacao = self.servico_documentos.receber_documento(
            usuario=usuario,
            nome_arquivo=arquivo.filename or "documento",
            tipo_mime=arquivo.content_type or "application/octet-stream",
            conteudo=conteudo,
            submission_id=submissao.id,
        )
        if validacao.status == ServicoDocumentosRecebidos.STATUS_REJEITADO:
            self.repositorio_auditoria.registrar(
                "documento.rejeitado",
                f"Documento {documento.id} rejeitado na triagem automatica.",
                submissao.id,
            )
            self.db.commit()
            raise ErroDominio(validacao.observacoes)

        comprovante_existente = self.repositorio_comprovantes.pegar_por_hash(documento.file_hash)
        if comprovante_existente:
            if not comprovante_existente.storage_path:
                comprovante_existente.storage_path = documento.storage_path
                comprovante_existente.stored_filename = documento.stored_filename
            if not comprovante_existente.extracted_text and documento.extracted_text:
                comprovante_existente.extracted_text = documento.extracted_text
            if not comprovante_existente.source_document_id:
                comprovante_existente.source_document_id = documento.id
            comprovante = comprovante_existente
        else:
            comprovante = Comprovante(
                user_id=submissao.user_id,
                original_filename=arquivo.filename or documento.stored_filename,
                stored_filename=documento.stored_filename,
                mime_type=arquivo.content_type or "application/octet-stream",
                file_hash=documento.file_hash,
                storage_path=documento.storage_path,
                file_content=None,
                extracted_text=documento.extracted_text,
                source_document_id=documento.id,
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
        self._aplicar_alertas_de_documento(submissao_atualizada, validacao)
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

    def remover_submissao(self, submissao_id: int) -> None:
        submissao = self.repositorio_submissoes.pegar(submissao_id)
        if not submissao:
            raise ErroDominio("Submissao nao encontrada.")

        comprovantes = [
            {"id": comprovante.id, "storage_path": comprovante.storage_path, "file_hash": comprovante.file_hash}
            for comprovante in submissao.evidence_files
        ]

        # Existing audit rows reference the submission via foreign key, so
        # they must be detached before the submission itself can be removed.
        self.repositorio_auditoria.desvincular_submissao(submissao_id)
        self.servico_documentos.desvincular_submissao(submissao_id)
        self.repositorio_submissoes.remover(submissao)
        self.db.flush()

        for comprovante in comprovantes:
            if self.repositorio_comprovantes.contar_vinculos(comprovante["id"]) > 0:
                continue
            entidade = self.repositorio_comprovantes.pegar(comprovante["id"])
            if not entidade:
                continue
            if self.servico_documentos.contar_por_hash(comprovante["file_hash"]) == 0:
                self.servico_arquivos.remover(entidade.storage_path or comprovante["storage_path"])
            self.repositorio_comprovantes.remover(entidade)

        self.repositorio_auditoria.registrar(
            "submissao.removida",
            f"Submissao {submissao_id} removida.",
            None,
        )
        self.db.commit()

    def delete_submission(self, submission_id: int) -> None:
        self.remover_submissao(submission_id)

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

    def _aplicar_alertas_de_documento(self, submissao: Submissao, validacao) -> None:
        if validacao.status != ServicoDocumentosRecebidos.STATUS_INCERTO:
            return

        notas = [validacao.observacoes]
        if submissao.review_notes:
            notas.append(submissao.review_notes)
        submissao.status = StatusSubmissao.PRECISA_REVISAO
        submissao.review_notes = " ".join(notas)
        self.repositorio_auditoria.registrar(
            "documento.incerto",
            "Documento anexado com baixa confianca automatica; submissao marcada para revisao.",
            submissao.id,
        )

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

