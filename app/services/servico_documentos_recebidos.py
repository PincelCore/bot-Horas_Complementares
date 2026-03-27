from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.configuracoes import pegar_configuracoes
from app.models import DocumentoRecebido, Usuario
from app.repositories.repositorio_documentos_recebidos import RepositorioDocumentosRecebidos
from app.services.armazenamento_arquivos import ServicoArquivos
from app.services.excecoes import ErroDominio


@dataclass
class ResultadoValidacaoDocumento:
    status: str
    score: int
    observacoes: str
    extracted_text: str | None


class ServicoDocumentosRecebidos:
    STATUS_ACEITO = "accepted"
    STATUS_INCERTO = "uncertain"
    STATUS_REJEITADO = "rejected"

    def __init__(self, db: Session):
        self.db = db
        self.configuracoes = pegar_configuracoes()
        self.repositorio_documentos = RepositorioDocumentosRecebidos(db)
        self.servico_arquivos = ServicoArquivos()

    def receber_documento(
        self,
        *,
        usuario: Usuario,
        nome_arquivo: str,
        tipo_mime: str,
        conteudo: bytes,
        submission_id: int | None = None,
    ) -> tuple[DocumentoRecebido, ResultadoValidacaoDocumento]:
        self._validar_limites(usuario.id)

        arquivo_preparado = self.servico_arquivos.salvar_bytes(
            nome_arquivo=nome_arquivo,
            tipo_mime=tipo_mime,
            conteudo=conteudo,
        )
        validacao = self._validar_documento(
            usuario=usuario,
            nome_arquivo=nome_arquivo,
            tipo_mime=tipo_mime,
            conteudo=conteudo,
        )
        documento = DocumentoRecebido(
            user_id=usuario.id,
            submission_id=submission_id,
            original_filename=nome_arquivo,
            stored_filename=arquivo_preparado.nome_interno,
            mime_type=tipo_mime,
            file_hash=arquivo_preparado.hash_arquivo,
            storage_path=arquivo_preparado.caminho_storage,
            size_bytes=len(conteudo),
            extracted_text=validacao.extracted_text,
            plausibility_status=validacao.status,
            plausibility_score=validacao.score,
            review_notes=validacao.observacoes,
        )
        return self.repositorio_documentos.criar(documento), validacao

    def limpar_expirados(self) -> int:
        limite = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=self.configuracoes.incoming_document_retention_days)
        expirados = self.repositorio_documentos.listar_expirados(limite)
        for documento in expirados:
            self.repositorio_documentos.remover(documento)
        if expirados:
            self.db.commit()
        return len(expirados)

    def desvincular_submissao(self, submission_id: int) -> None:
        for documento in self.repositorio_documentos.listar_por_submissao(submission_id):
            documento.submission_id = None
        self.db.flush()

    def contar_por_hash(self, file_hash: str) -> int:
        return self.repositorio_documentos.contar_por_hash(file_hash)

    def _validar_limites(self, user_id: int) -> None:
        agora = datetime.now(UTC).replace(tzinfo=None)
        por_hora = self.repositorio_documentos.contar_por_usuario_desde(user_id, agora - timedelta(hours=1))
        if por_hora >= self.configuracoes.max_documents_per_user_per_hour:
            raise ErroDominio("Você já enviou muitos arquivos nesta última hora. Tenta de novo daqui a pouco.")

        por_dia = self.repositorio_documentos.contar_por_usuario_desde(user_id, agora - timedelta(days=1))
        if por_dia >= self.configuracoes.max_documents_per_user_per_day:
            raise ErroDominio("Você já atingiu o limite diário de arquivos. Amanhã você pode tentar de novo.")

    def _validar_documento(
        self,
        *,
        usuario: Usuario,
        nome_arquivo: str,
        tipo_mime: str,
        conteudo: bytes,
    ) -> ResultadoValidacaoDocumento:
        texto_extraido = self._extrair_texto(nome_arquivo=nome_arquivo, tipo_mime=tipo_mime, conteudo=conteudo)
        if not texto_extraido:
            return ResultadoValidacaoDocumento(
                status=self.STATUS_INCERTO,
                score=0,
                observacoes="Não consegui ler texto suficiente do arquivo. Vou deixar para revisão manual se você usar esse comprovante.",
                extracted_text=None,
            )

        texto_normalizado = self._normalizar_texto(texto_extraido)
        score = 0

        positivos = {
            "certificado": 3,
            "declaracao": 2,
            "participacao": 2,
            "participou": 2,
            "conclusao": 2,
            "concluiu": 2,
            "carga horaria": 2,
            "horas": 1,
            "evento": 1,
            "curso": 1,
            "seminario": 1,
            "congresso": 1,
            "palestra": 1,
            "simposio": 1,
            "oficina": 1,
            "apresentacao": 1,
            "extensao": 1,
            "monitoria": 1,
            "estagio": 1,
        }
        negativos = {
            "boleto": -4,
            "nota fiscal": -4,
            "pix": -3,
            "fatura": -3,
            "cpf": -3,
            "rg": -3,
            "identidade": -3,
            "extrato": -3,
            "whatsapp": -3,
            "conversa": -3,
            "pedido": -2,
            "comprovante de residencia": -4,
        }

        for termo, peso in positivos.items():
            if termo in texto_normalizado:
                score += peso
        for termo, peso in negativos.items():
            if termo in texto_normalizado:
                score += peso

        nome_usuario = self._normalizar_texto(usuario.full_name)
        if nome_usuario and nome_usuario in texto_normalizado:
            score += 2

        if score <= -2:
            return ResultadoValidacaoDocumento(
                status=self.STATUS_REJEITADO,
                score=score,
                observacoes="Esse arquivo não parece um certificado ou comprovante de atividade acadêmica. Confere se você anexou o PDF certo.",
                extracted_text=texto_extraido[:5000],
            )
        if score >= 4:
            return ResultadoValidacaoDocumento(
                status=self.STATUS_ACEITO,
                score=score,
                observacoes="O arquivo parece compatível com um certificado ou comprovante de atividade.",
                extracted_text=texto_extraido[:5000],
            )
        return ResultadoValidacaoDocumento(
            status=self.STATUS_INCERTO,
            score=score,
            observacoes="O arquivo não parece claramente inválido, mas também não deu para confirmar com segurança que é um certificado.",
            extracted_text=texto_extraido[:5000],
        )

    def _extrair_texto(self, *, nome_arquivo: str, tipo_mime: str, conteudo: bytes) -> str | None:
        if tipo_mime != "application/pdf":
            return None

        texto = self._extrair_texto_pdf_com_pypdf(conteudo)
        if texto:
            return texto
        return self._extrair_texto_pdf_por_regex(conteudo)

    @staticmethod
    def _extrair_texto_pdf_com_pypdf(conteudo: bytes) -> str | None:
        try:
            from io import BytesIO

            from pypdf import PdfReader
        except ModuleNotFoundError:
            return None
        except Exception:
            return None

        try:
            leitor = PdfReader(BytesIO(conteudo))
            partes = [pagina.extract_text() or "" for pagina in leitor.pages]
        except Exception:
            return None
        texto = "\n".join(parte.strip() for parte in partes if parte and parte.strip())
        return texto or None

    @staticmethod
    def _extrair_texto_pdf_por_regex(conteudo: bytes) -> str | None:
        trechos = re.findall(rb"\(([^()]*)\)", conteudo)
        if not trechos:
            return None
        partes: list[str] = []
        for trecho in trechos:
            try:
                texto = trecho.decode("latin-1", errors="ignore").strip()
            except Exception:
                continue
            if len(texto) >= 3:
                partes.append(texto)
        return "\n".join(partes) or None

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        sem_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"\s+", " ", sem_acentos).strip().lower()
