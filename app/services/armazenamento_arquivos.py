import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.configuracoes import pegar_configuracoes
from app.services.excecoes import ErroDominio


@dataclass
class ArquivoPreparado:
    nome_interno: str
    caminho_storage: str
    hash_arquivo: str
    conteudo: bytes


class ServicoArquivos:
    def __init__(self) -> None:
        self.configuracoes = pegar_configuracoes()

    def salvar(self, arquivo: UploadFile) -> ArquivoPreparado:
        conteudo = arquivo.file.read()
        return self.salvar_bytes(
            nome_arquivo=arquivo.filename or "documento",
            tipo_mime=arquivo.content_type or "application/octet-stream",
            conteudo=conteudo,
        )

    def save(self, upload: UploadFile) -> ArquivoPreparado:
        return self.salvar(upload)

    def salvar_bytes(self, *, nome_arquivo: str, tipo_mime: str, conteudo: bytes) -> ArquivoPreparado:
        limite_bytes = self.configuracoes.max_upload_size_mb * 1024 * 1024
        if len(conteudo) > limite_bytes:
            raise ErroDominio("Arquivo excede o limite configurado.")
        if tipo_mime not in self.configuracoes.allowed_mime_types:
            raise ErroDominio("Tipo de arquivo nao permitido.")

        sufixo = Path(nome_arquivo or "documento").suffix
        nome_interno = f"{uuid4().hex}{sufixo}"
        hash_arquivo = hashlib.sha256(conteudo).hexdigest()
        return ArquivoPreparado(
            nome_interno=nome_interno,
            caminho_storage=f"db://evidences/{nome_interno}",
            hash_arquivo=hash_arquivo,
            conteudo=conteudo,
        )

    def save_bytes(self, *, filename: str, mime_type: str, content: bytes) -> ArquivoPreparado:
        return self.salvar_bytes(nome_arquivo=filename, tipo_mime=mime_type, conteudo=content)

    @staticmethod
    def criar_upload_file(*, nome_arquivo: str, tipo_mime: str, conteudo: bytes) -> UploadFile:
        return UploadFile(filename=nome_arquivo, file=io.BytesIO(conteudo), headers={"content-type": tipo_mime})

    @staticmethod
    def make_upload_file(*, filename: str, mime_type: str, content: bytes) -> UploadFile:
        return ServicoArquivos.criar_upload_file(nome_arquivo=filename, tipo_mime=mime_type, conteudo=content)

    @staticmethod
    def remover(caminho_salvo: str) -> None:
        if caminho_salvo.startswith("db://"):
            return
        caminho = Path(caminho_salvo)
        if caminho.exists():
            caminho.unlink()

    @staticmethod
    def delete(stored_path: str) -> None:
        ServicoArquivos.remover(stored_path)


FileStorageService = ServicoArquivos

