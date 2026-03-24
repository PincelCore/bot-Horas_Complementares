from __future__ import annotations

from sqlalchemy.orm import Session

from app.bot.cliente_telegram import ClienteTelegram
from app.domain.enumeracoes import EstadoBot, TipoRegra, StatusSubmissao
from app.models import Regra, Usuario
from app.repositories.repositorio_categorias import RepositorioCategorias
from app.repositories.repositorio_regras import RepositorioRegras
from app.repositories.repositorio_usuarios import RepositorioUsuarios
from app.schemas.submissao import SubmissaoCriacao
from app.schemas.usuario import UsuarioCriacao
from app.services.excecoes import ErroDominio
from app.services.servico_submissoes import ServicoSubmissoes
from app.services.servico_usuarios import ServicoUsuarios


TEXTO_BOTAO_NOVA = "Nova atividade"
TEXTO_BOTAO_MINHAS = "Minhas atividades"
TEXTO_BOTAO_RESUMO = "Resumo"
TEXTO_BOTAO_REGRAS = "Regras"
TEXTO_BOTAO_COMPROVANTES = "Comprovantes"
TEXTO_BOTAO_FINALIZAR = "Finalizar envio"
TEXTO_BOTAO_CANCELAR = "Cancelar"


class ServicoTelegram:
    def __init__(self, db: Session):
        self.db = db
        self.repositorio_usuarios = RepositorioUsuarios(db)
        self.repositorio_categorias = RepositorioCategorias(db)
        self.repositorio_regras = RepositorioRegras(db)
        self.servico_usuarios = ServicoUsuarios(db)
        self.servico_submissoes = ServicoSubmissoes(db)
        self.cliente_telegram = ClienteTelegram()

    def processar_update(self, update: dict) -> str:
        callback = update.get("callback_query")
        if callback:
            return self._processar_callback(callback)

        mensagem = update.get("message") or update.get("edited_message") or {}
        chat = mensagem.get("chat", {})
        chat_id = chat.get("id")
        if not chat_id:
            return "Update ignorado."

        usuario = self.repositorio_usuarios.get_by_telegram_chat_id(chat_id)
        texto = (mensagem.get("text") or "").strip()

        if self._eh_inicio(texto):
            resposta = self._lidar_com_inicio(mensagem, chat_id, usuario)
            self._enviar_texto(chat_id, resposta)
            return resposta

        if not usuario:
            resposta = "Manda um /start primeiro pra eu te cadastrar."
            self._enviar_texto(chat_id, resposta)
            return resposta

        if mensagem.get("document") or mensagem.get("photo"):
            resposta = self._lidar_com_midias(usuario, mensagem)
            self._enviar_texto(chat_id, resposta, marcacao_inline=self._acoes_submissao_inline(usuario))
            return resposta

        resposta, marcacao_inline = self._rotear_texto(usuario, texto)
        self._enviar_texto(chat_id, resposta, marcacao_inline=marcacao_inline)
        return resposta

    def process_update(self, update: dict) -> str:
        return self.processar_update(update)

    def _processar_callback(self, callback: dict) -> str:
        mensagem = callback.get("message", {})
        chat = mensagem.get("chat", {})
        chat_id = chat.get("id")
        callback_id = callback.get("id")
        dados = callback.get("data") or ""

        if callback_id:
            try:
                self.cliente_telegram.responder_callback(callback_id)
            except Exception:
                pass

        if not chat_id:
            return "Callback ignorado."

        usuario = self.repositorio_usuarios.get_by_telegram_chat_id(chat_id)
        if not usuario:
            resposta = "Manda um /start primeiro pra eu te cadastrar."
            self._enviar_texto(chat_id, resposta)
            return resposta

        if dados.startswith("categoria:"):
            codigo_categoria = dados.split(":", 1)[1]
            resposta = self._lidar_com_categoria_por_botao(usuario, codigo_categoria)
            self._enviar_texto(chat_id, resposta)
            return resposta

        if dados.startswith("remover:"):
            _, submissao_id, comprovante_id = dados.split(":")
            resposta = self._remover_comprovante_por_botao(usuario, int(submissao_id), int(comprovante_id))
            self._enviar_texto(chat_id, resposta, marcacao_inline=self._acoes_submissao_inline(usuario))
            return resposta

        if dados == "ver_comprovantes":
            resposta, marcacao_inline = self._listar_comprovantes(usuario)
            self._enviar_texto(chat_id, resposta, marcacao_inline=marcacao_inline)
            return resposta

        if dados == "finalizar_envio":
            resposta = self._finalizar_submissao(usuario)
            self._enviar_texto(chat_id, resposta)
            return resposta

        resposta = "Nao entendi esse botao, tenta de novo."
        self._enviar_texto(chat_id, resposta)
        return resposta

    def _rotear_texto(self, usuario: Usuario, texto: str) -> tuple[str, dict | None]:
        texto_normalizado = (texto or "").strip()

        if self._eh_nova_atividade(texto_normalizado):
            return self._abrir_fluxo_nova_atividade(usuario), self._teclado_categorias()
        if self._eh_minhas_atividades(texto_normalizado):
            return self._minhas_atividades(usuario.id), None
        if self._eh_resumo(texto_normalizado):
            return self._resumo(usuario.id), None
        if self._eh_regras(texto_normalizado):
            return self._regras(), None
        if self._eh_comprovantes(texto_normalizado):
            return self._listar_comprovantes(usuario)
        if self._eh_finalizar(texto_normalizado):
            return self._finalizar_submissao(usuario), None
        if self._eh_cancelar(texto_normalizado):
            return self._cancelar_fluxo(usuario), None

        if usuario.bot_state == EstadoBot.AGUARDANDO_TITULO.value:
            return self._guardar_titulo(usuario, texto_normalizado), None
        if usuario.bot_state == EstadoBot.AGUARDANDO_NUMERO.value:
            return self._guardar_numero_atividade(usuario, texto_normalizado), self._acoes_submissao_inline(usuario)
        if usuario.bot_state == EstadoBot.AGUARDANDO_CATEGORIA.value:
            return "Escolhe a categoria clicando num botao logo acima.", self._teclado_categorias()

        return "Toca num botao do menu pra eu te guiar melhor.", None

    def _lidar_com_inicio(self, mensagem: dict, chat_id: int, usuario: Usuario | None) -> str:
        nome_completo = " ".join(
            filter(None, [mensagem.get("from", {}).get("first_name"), mensagem.get("from", {}).get("last_name")])
        ) or "Aluno"
        if not usuario:
            usuario = self.servico_usuarios.criar_usuario(
                UsuarioCriacao(
                    full_name=nome_completo,
                    telegram_chat_id=chat_id,
                    telegram_username=mensagem.get("from", {}).get("username"),
                )
            )
        return (
            f"Fechou, {usuario.full_name}! Eu vou te ajudar com as horas complementares.\n"
            "Usa os botoes aqui embaixo. O fluxo agora ficou simples: titulo, categoria e um numero da atividade."
        )

    def _abrir_fluxo_nova_atividade(self, usuario: Usuario) -> str:
        usuario.bot_state = EstadoBot.AGUARDANDO_CATEGORIA.value
        usuario.active_submission_id = None
        self.db.commit()
        return "Boa. Primeiro escolhe a categoria no painel de botoes que eu te mandei."

    def _lidar_com_categoria_por_botao(self, usuario: Usuario, codigo_categoria: str) -> str:
        categoria = self.repositorio_categorias.get_by_code(codigo_categoria)
        if not categoria:
            return "Nao achei essa categoria. Clica em Nova atividade de novo."

        submissao = self.servico_submissoes.criar_submissao(
            SubmissaoCriacao(
                user_id=usuario.id,
                category_code=categoria.code,
                title=f"Submissao {categoria.name}",
                status=StatusSubmissao.RASCUNHO,
            )
        )
        usuario.active_submission_id = submissao.id
        usuario.bot_state = EstadoBot.AGUARDANDO_TITULO.value
        self.db.commit()
        return f"Categoria escolhida: {categoria.name}. Agora me manda so o titulo da atividade."

    def _guardar_titulo(self, usuario: Usuario, texto: str) -> str:
        if not texto:
            return "Manda um titulo de verdade pra eu continuar."
        if len(texto) < 3:
            return "Titulo muito curtinho. Manda algo com pelo menos 3 caracteres."

        submissao = self.servico_submissoes.pegar_submissao(usuario.active_submission_id or 0)
        if not submissao:
            usuario.bot_state = EstadoBot.PARADO.value
            usuario.active_submission_id = None
            self.db.commit()
            return "Perdi a submissao no meio do caminho. Toca em Nova atividade de novo."

        submissao.title = texto[:255]
        usuario.bot_state = EstadoBot.AGUARDANDO_NUMERO.value
        self.db.commit()
        return "Show. Agora manda um numero da atividade. Se a regra for por mes/evento/semestre, manda a quantidade. Se for por horas, manda as horas."

    def _guardar_numero_atividade(self, usuario: Usuario, texto: str) -> str:
        submissao = self.servico_submissoes.pegar_submissao(usuario.active_submission_id or 0)
        if not submissao:
            usuario.bot_state = EstadoBot.PARADO.value
            usuario.active_submission_id = None
            self.db.commit()
            return "Perdi a submissao no meio do caminho. Toca em Nova atividade de novo."

        try:
            valor = float(texto.replace(",", "."))
        except ValueError:
            return "Esse numero nao rolou. Manda algo tipo 2, 3.5, 10..."

        if valor <= 0:
            return "O valor precisa ser maior que zero."

        regra = self._pegar_regra_principal(submissao.category_id)
        if regra and regra.rule_type == TipoRegra.POR_UNIDADE:
            submissao.declared_quantity = valor
            submissao.declared_hours = None
        else:
            submissao.declared_hours = valor
            submissao.declared_quantity = None

        usuario.bot_state = EstadoBot.AGUARDANDO_COMPROVANTE.value
        self.db.commit()
        return "Perfeito. Agora so me manda o certificado em PDF ou imagem aqui no chat."

    def _lidar_com_midias(self, usuario: Usuario, mensagem: dict) -> str:
        if not usuario.active_submission_id:
            return "Recebi o arquivo, mas voce nao abriu uma atividade ainda. Toca em Nova atividade primeiro."

        submissao = self.servico_submissoes.pegar_submissao(usuario.active_submission_id)
        if not submissao or submissao.user_id != usuario.id:
            return "Nao achei sua atividade aberta. Toca em Nova atividade de novo."

        if usuario.bot_state != EstadoBot.AGUARDANDO_COMPROVANTE.value:
            return "Antes do certificado eu preciso que voce termine titulo e numero da atividade."

        try:
            nome_arquivo, tipo_mime, file_id = self._extrair_dados_arquivo(mensagem)
            info_arquivo = self.cliente_telegram.buscar_arquivo(file_id)
            caminho_arquivo = info_arquivo.get("file_path")
            if not caminho_arquivo:
                raise ErroDominio("O Telegram nao mandou o caminho do arquivo.")
            conteudo = self.cliente_telegram.baixar_arquivo(caminho_arquivo)
            atualizada = self.servico_submissoes.adicionar_comprovante_por_bytes(
                submissao.id,
                nome_arquivo=nome_arquivo,
                tipo_mime=tipo_mime,
                conteudo=conteudo,
            )
        except ErroDominio as erro:
            return str(erro)

        estimativa = f"{atualizada.estimated_hours:.2f}h" if atualizada.estimated_hours is not None else "sem estimativa"
        return (
            f"Certificado anexado na atividade #{atualizada.id}. "
            f"Status agora: {atualizada.status.value}. Estimativa atual: {estimativa}."
        )

    def _listar_comprovantes(self, usuario: Usuario) -> tuple[str, dict | None]:
        if not usuario.active_submission_id:
            return "Nao tem atividade aberta agora. Se quiser ver as antigas, toca em Minhas atividades.", None

        submissao = self.servico_submissoes.pegar_submissao(usuario.active_submission_id)
        if not submissao or submissao.user_id != usuario.id:
            return "Nao achei a atividade aberta.", None

        comprovantes = submissao.evidence_files
        if not comprovantes:
            return "Ainda nao tem comprovante anexado nessa atividade.", self._acoes_submissao_inline(usuario)

        linhas = [f"Comprovantes da atividade #{submissao.id}:"]
        for comprovante in comprovantes:
            linhas.append(f"- {comprovante.id}: {comprovante.original_filename}")
        return "\n".join(linhas), self._teclado_comprovantes(submissao.id, comprovantes)

    def _remover_comprovante_por_botao(self, usuario: Usuario, submissao_id: int, comprovante_id: int) -> str:
        submissao = self.servico_submissoes.pegar_submissao(submissao_id)
        if not submissao or submissao.user_id != usuario.id:
            return "Nao achei essa atividade."

        atualizada = self.servico_submissoes.remover_comprovante(submissao_id, comprovante_id)
        estimativa = f"{atualizada.estimated_hours:.2f}h" if atualizada.estimated_hours is not None else "sem estimativa"
        return f"Pronto, removi o comprovante. A atividade ficou com status {atualizada.status.value} e estimativa {estimativa}."

    def _finalizar_submissao(self, usuario: Usuario) -> str:
        if not usuario.active_submission_id:
            return "Nao tem atividade aberta pra finalizar."

        rascunho = self.servico_submissoes.pegar_submissao(usuario.active_submission_id)
        if not rascunho:
            usuario.bot_state = EstadoBot.PARADO.value
            usuario.active_submission_id = None
            self.db.commit()
            return "Perdi a atividade aberta. Toca em Nova atividade de novo."

        rascunho.status = StatusSubmissao.ENVIADA
        finalizada = self.servico_submissoes.avaliar_submissao(usuario.active_submission_id)
        usuario.bot_state = EstadoBot.PARADO.value
        usuario.active_submission_id = None
        self.db.commit()

        estimativa = f"{finalizada.estimated_hours:.2f}h" if finalizada.estimated_hours is not None else "sem estimativa"
        observacao = f"\nObs: {finalizada.review_notes}" if finalizada.review_notes else ""
        return f"Fechou. Atividade #{finalizada.id} enviada com status {finalizada.status.value} e estimativa {estimativa}.{observacao}"

    def _cancelar_fluxo(self, usuario: Usuario) -> str:
        usuario.bot_state = EstadoBot.PARADO.value
        usuario.active_submission_id = None
        self.db.commit()
        return "Cancelei o fluxo por aqui. Quando quiser, toca em Nova atividade."

    def _minhas_atividades(self, usuario_id: int) -> str:
        submissoes = self.servico_submissoes.listar_submissoes_do_usuario(usuario_id)
        if not submissoes:
            return "Voce ainda nao tem nenhuma atividade cadastrada."
        linhas = ["Suas atividades:"]
        for submissao in submissoes[:10]:
            estimativa = f"{submissao.estimated_hours:.2f}h" if submissao.estimated_hours is not None else "sem estimativa"
            linhas.append(f"- #{submissao.id} {submissao.title} [{submissao.status.value}] - {estimativa}")
        return "\n".join(linhas)

    def _resumo(self, usuario_id: int) -> str:
        resumo = self.servico_usuarios.pegar_resumo(usuario_id)
        linhas = [
            f"Voce tem {resumo.total_estimated_hours:.2f}h estimadas.",
            f"A meta oficial e {resumo.required_hours:.0f}h.",
            f"Ainda faltam {resumo.remaining_hours:.2f}h.",
        ]
        linhas.extend(f"- {categoria.category_name}: {categoria.total_hours:.2f}h" for categoria in resumo.categories)
        return "\n".join(linhas)

    def _regras(self) -> str:
        regras = self.repositorio_regras.list_all()
        if not regras:
            return "Ainda nao tem regra cadastrada."
        linhas = ["Regras oficiais carregadas:"]
        for regra in regras:
            linhas.append(f"- {regra.category.name}: {regra.short_description}")
        return "\n".join(linhas)

    def _pegar_regra_principal(self, categoria_id: int | None) -> Regra | None:
        if categoria_id is None:
            return None
        regras = self.repositorio_regras.get_by_category(categoria_id)
        return regras[0] if regras else None

    def _enviar_texto(self, chat_id: int, texto: str, marcacao_inline: dict | None = None) -> None:
        marcacao = marcacao_inline or self._menu_principal()
        try:
            self.cliente_telegram.enviar_mensagem(chat_id, texto, marcacao=marcacao)
        except Exception:
            return

    @staticmethod
    def _menu_principal() -> dict:
        return {
            "keyboard": [
                [{"text": TEXTO_BOTAO_NOVA}, {"text": TEXTO_BOTAO_MINHAS}],
                [{"text": TEXTO_BOTAO_RESUMO}, {"text": TEXTO_BOTAO_REGRAS}],
                [{"text": TEXTO_BOTAO_COMPROVANTES}, {"text": TEXTO_BOTAO_FINALIZAR}],
                [{"text": TEXTO_BOTAO_CANCELAR}],
            ],
            "resize_keyboard": True,
            "is_persistent": True,
        }

    def _teclado_categorias(self) -> dict:
        categorias = self.repositorio_categorias.list_all()
        linhas: list[list[dict[str, str]]] = []
        linha_atual: list[dict[str, str]] = []
        for categoria in categorias:
            linha_atual.append({"text": categoria.name, "callback_data": f"categoria:{categoria.code}"})
            if len(linha_atual) == 2:
                linhas.append(linha_atual)
                linha_atual = []
        if linha_atual:
            linhas.append(linha_atual)
        return {"inline_keyboard": linhas}

    def _teclado_comprovantes(self, submissao_id: int, comprovantes: list) -> dict:
        linhas = [
            [{"text": f"Remover {comprovante.original_filename}", "callback_data": f"remover:{submissao_id}:{comprovante.id}"}]
            for comprovante in comprovantes
        ]
        linhas.append([{"text": "Finalizar envio", "callback_data": "finalizar_envio"}])
        return {"inline_keyboard": linhas}

    def _acoes_submissao_inline(self, usuario: Usuario) -> dict | None:
        if not usuario.active_submission_id:
            return None
        return {
            "inline_keyboard": [
                [{"text": "Ver comprovantes", "callback_data": "ver_comprovantes"}],
                [{"text": "Finalizar envio", "callback_data": "finalizar_envio"}],
            ]
        }

    @staticmethod
    def _extrair_dados_arquivo(mensagem: dict) -> tuple[str, str, str]:
        if mensagem.get("document"):
            documento = mensagem["document"]
            return (
                documento.get("file_name") or f"{documento.get('file_unique_id', documento['file_id'])}.bin",
                documento.get("mime_type") or "application/octet-stream",
                documento["file_id"],
            )

        fotos = mensagem.get("photo") or []
        if fotos:
            selecionada = fotos[-1]
            nome_base = selecionada.get("file_unique_id") or selecionada["file_id"]
            return f"{nome_base}.jpg", "image/jpeg", selecionada["file_id"]

        raise ErroDominio("Nao achei um arquivo valido nessa mensagem.")

    @staticmethod
    def _eh_inicio(texto: str) -> bool:
        return texto.startswith("/start") or texto == "Comecar"

    @staticmethod
    def _eh_nova_atividade(texto: str) -> bool:
        return texto.startswith("/nova") or texto == TEXTO_BOTAO_NOVA

    @staticmethod
    def _eh_minhas_atividades(texto: str) -> bool:
        return texto.startswith("/minhas") or texto == TEXTO_BOTAO_MINHAS

    @staticmethod
    def _eh_resumo(texto: str) -> bool:
        return texto.startswith("/resumo") or texto == TEXTO_BOTAO_RESUMO

    @staticmethod
    def _eh_regras(texto: str) -> bool:
        return texto.startswith("/regras") or texto == TEXTO_BOTAO_REGRAS

    @staticmethod
    def _eh_comprovantes(texto: str) -> bool:
        return texto.startswith("/comprovantes") or texto == TEXTO_BOTAO_COMPROVANTES

    @staticmethod
    def _eh_finalizar(texto: str) -> bool:
        return texto.startswith("/enviar") or texto == TEXTO_BOTAO_FINALIZAR

    @staticmethod
    def _eh_cancelar(texto: str) -> bool:
        return texto.startswith("/cancelar") or texto == TEXTO_BOTAO_CANCELAR


TelegramBotService = ServicoTelegram

