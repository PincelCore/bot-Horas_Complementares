import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

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

        sufixo = (Path(nome_arquivo or "documento").suffix or "").lower()
        hash_arquivo = hashlib.sha256(conteudo).hexdigest()
        nome_interno = f"{hash_arquivo}{sufixo}" if sufixo else hash_arquivo
        caminho_storage = self._salvar_backend(nome_interno=nome_interno, conteudo=conteudo, tipo_mime=tipo_mime)
        return ArquivoPreparado(
            nome_interno=nome_interno,
            caminho_storage=caminho_storage,
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
        if caminho_salvo.startswith("file://"):
            caminho = Path(caminho_salvo.replace("file://", "", 1))
            if caminho.exists():
                caminho.unlink()
            return
        if caminho_salvo.startswith("s3://"):
            ServicoArquivos()._remover_do_s3(caminho_salvo)

    @staticmethod
    def delete(stored_path: str) -> None:
        ServicoArquivos.remover(stored_path)

    def _salvar_backend(self, *, nome_interno: str, conteudo: bytes, tipo_mime: str) -> str:
        if self.configuracoes.storage_backend == "s3":
            return self._salvar_no_s3(nome_interno=nome_interno, conteudo=conteudo, tipo_mime=tipo_mime)
        return self._salvar_no_filesystem(nome_interno=nome_interno, conteudo=conteudo)

    def _salvar_no_filesystem(self, *, nome_interno: str, conteudo: bytes) -> str:
        prefixo = self.configuracoes.storage_key_prefix.strip("/\\")
        pasta_destino = self.configuracoes.storage_dir / prefixo if prefixo else self.configuracoes.storage_dir
        pasta_destino.mkdir(parents=True, exist_ok=True)
        caminho = pasta_destino / nome_interno
        if not caminho.exists():
            caminho.write_bytes(conteudo)
        return f"file://{caminho.resolve()}"

    def _salvar_no_s3(self, *, nome_interno: str, conteudo: bytes, tipo_mime: str) -> str:
        bucket = self.configuracoes.storage_bucket
        endpoint = self.configuracoes.storage_endpoint_url
        if not bucket or not endpoint:
            raise ErroDominio("Storage S3/R2 nao configurado por completo.")

        try:
            import boto3
        except ModuleNotFoundError as exc:
            raise ErroDominio("Dependencia boto3 ausente para usar STORAGE_BACKEND=s3.") from exc

        cliente = boto3.client(
            "s3",
            region_name=self.configuracoes.storage_region,
            endpoint_url=endpoint,
            aws_access_key_id=self.configuracoes.storage_access_key_id or None,
            aws_secret_access_key=self.configuracoes.storage_secret_access_key or None,
        )
        chave = self._chave_storage(nome_interno)
        cliente.put_object(Bucket=bucket, Key=chave, Body=conteudo, ContentType=tipo_mime)
        return f"s3://{bucket}/{chave}"

    def _remover_do_s3(self, caminho_salvo: str) -> None:
        bucket, chave = self._separar_caminho_s3(caminho_salvo)
        if not bucket or not chave:
            return
        if not self.configuracoes.storage_endpoint_url:
            return
        try:
            import boto3
        except ModuleNotFoundError:
            return
        cliente = boto3.client(
            "s3",
            region_name=self.configuracoes.storage_region,
            endpoint_url=self.configuracoes.storage_endpoint_url,
            aws_access_key_id=self.configuracoes.storage_access_key_id or None,
            aws_secret_access_key=self.configuracoes.storage_secret_access_key or None,
        )
        cliente.delete_object(Bucket=bucket, Key=chave)

    def _chave_storage(self, nome_interno: str) -> str:
        prefixo = self.configuracoes.storage_key_prefix.strip("/\\")
        return f"{prefixo}/{nome_interno}" if prefixo else nome_interno

    @staticmethod
    def _separar_caminho_s3(caminho_salvo: str) -> tuple[str, str]:
        sem_esquema = caminho_salvo.replace("s3://", "", 1)
        if "/" not in sem_esquema:
            return sem_esquema, ""
        bucket, chave = sem_esquema.split("/", 1)
        return bucket, chave


FileStorageService = ServicoArquivos

