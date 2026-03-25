from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.bot.cliente_telegram import ClienteTelegram
from app.domain.enumeracoes import EstadoBot, TipoRegra, StatusSubmissao, UnidadeQuantidade
from app.models import Regra, Submissao, Usuario
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
TEXTO_BOTAO_AJUDA_CATEGORIA = "Qual categoria usar?"


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
            resposta = "Manda um /start primeiro para eu te cadastrar."
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
            resposta = "Manda um /start primeiro para eu te cadastrar."
            self._enviar_texto(chat_id, resposta)
            return resposta

        if dados.startswith("categoria:"):
            codigo_categoria = dados.split(":", 1)[1]
            resposta = self._lidar_com_categoria_por_botao(usuario, codigo_categoria)
            self._enviar_texto(chat_id, resposta)
            return resposta

        if dados.startswith("valor:"):
            valor = dados.split(":", 1)[1]
            resposta = self._guardar_numero_atividade(usuario, valor)
            self._enviar_texto(chat_id, resposta, marcacao_inline=self._acoes_submissao_inline(usuario))
            return resposta

        if dados == "ajuda_categorias":
            resposta = self._texto_ajuda_categorias()
            self._enviar_texto(chat_id, resposta, marcacao_inline=self._teclado_categorias())
            return resposta

        if dados == "nova_atividade":
            resposta = self._abrir_fluxo_nova_atividade(usuario)
            self._enviar_texto(chat_id, resposta, marcacao_inline=self._teclado_categorias())
            return resposta

        if dados.startswith("atividade:"):
            submissao_id = dados.split(":", 1)[1]
            resposta = self._selecionar_atividade_por_botao(usuario, submissao_id)
            self._enviar_texto(chat_id, resposta, marcacao_inline=self._acoes_submissao_inline(usuario))
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
            self._enviar_texto(chat_id, resposta, marcacao_inline=self._acoes_submissao_inline(usuario))
            return resposta

        resposta = "Não entendi esse botão. Tenta de novo."
        self._enviar_texto(chat_id, resposta)
        return resposta

    def _rotear_texto(self, usuario: Usuario, texto: str) -> tuple[str, dict | None]:
        texto_normalizado = (texto or "").strip()

        if self._eh_nova_atividade(texto_normalizado):
            return self._abrir_fluxo_nova_atividade(usuario), self._teclado_categorias()
        if self._eh_minhas_atividades(texto_normalizado):
            return self._minhas_atividades(usuario)
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
            resposta = self._guardar_titulo(usuario, texto_normalizado)
            marcacao_inline = self._teclado_medida_do_usuario(usuario)
            return resposta, marcacao_inline
        if usuario.bot_state == EstadoBot.AGUARDANDO_NUMERO.value:
            return self._guardar_numero_atividade(usuario, texto_normalizado), self._acoes_submissao_inline(usuario)
        if usuario.bot_state == EstadoBot.AGUARDANDO_CATEGORIA.value:
            return "Escolhe a categoria tocando em um botão logo acima.", self._teclado_categorias()

        return "Toca em um botão do menu para eu te guiar melhor.", None

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
            f"Fechou, {usuario.full_name}.\n\n"
            "Eu vou te ajudar a lançar as horas complementares por aqui.\n"
            "Você escolhe a categoria e eu peço só o dado que essa regra realmente precisa."
        )

    def _abrir_fluxo_nova_atividade(self, usuario: Usuario) -> str:
        usuario.bot_state = EstadoBot.AGUARDANDO_CATEGORIA.value
        usuario.active_submission_id = None
        self.db.commit()
        return (
            "Beleza. Primeiro escolhe a categoria.\n\n"
            "Dica rápida:\n"
            "• Se você foi a uma palestra, seminário, congresso, simpósio, feira ou evento parecido como participante, "
            "normalmente é Ouvinte em Eventos.\n"
            "• Se você apresentou trabalho no evento, aí costuma ser Apresentação de Trabalhos."
        )

    def _lidar_com_categoria_por_botao(self, usuario: Usuario, codigo_categoria: str) -> str:
        categoria = self.repositorio_categorias.get_by_code(codigo_categoria)
        if not categoria:
            return "Não achei essa categoria. Toca em Nova atividade de novo."

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
        regra = self._pegar_regra_principal(submissao.category_id)
        explicacao = self._explicacao_categoria(categoria.code)
        linha_regra = f"Como essa categoria funciona: {self._resumo_regra(regra)}." if regra else ""
        return "\n".join(
            parte
            for parte in [
                f"Categoria escolhida: {categoria.name}.",
                explicacao,
                linha_regra,
                "Agora me manda o título da atividade.",
            ]
            if parte
        )

    def _selecionar_atividade_por_botao(self, usuario: Usuario, submissao_id: str) -> str:
        if not submissao_id.isdigit():
            return "Esse botão veio quebrado. Toca em Minhas atividades de novo."

        submissao = self.servico_submissoes.pegar_submissao(int(submissao_id))
        if not submissao or submissao.user_id != usuario.id:
            return "Não achei essa atividade."

        usuario.active_submission_id = submissao.id
        usuario.bot_state = EstadoBot.PARADO.value
        self.db.commit()
        return (
            f"Atividade aberta: #{submissao.id} - {submissao.title}\n"
            f"Categoria: {submissao.category_name or 'Sem categoria'}\n"
            f"Status: {self._rotulo_status(submissao.status)}\n"
            f"Horas estimadas: {self._formatar_horas(submissao.estimated_hours)}\n"
            "Se precisar corrigir arquivo, toca em Ver comprovantes."
        )

    def _guardar_titulo(self, usuario: Usuario, texto: str) -> str:
        if not texto:
            return "Me manda um título de verdade para eu continuar."
        if len(texto) < 3:
            return "Título muito curtinho. Manda algo com pelo menos 3 caracteres."

        submissao = self.servico_submissoes.pegar_submissao(usuario.active_submission_id or 0)
        if not submissao:
            usuario.bot_state = EstadoBot.PARADO.value
            usuario.active_submission_id = None
            self.db.commit()
            return "Perdi a submissão no meio do caminho. Toca em Nova atividade de novo."

        submissao.title = texto[:255]
        usuario.bot_state = EstadoBot.AGUARDANDO_NUMERO.value
        self.db.commit()
        regra = self._pegar_regra_principal(submissao.category_id)
        return self._texto_pedir_medida(submissao, regra)

    def _guardar_numero_atividade(self, usuario: Usuario, texto: str) -> str:
        submissao = self.servico_submissoes.pegar_submissao(usuario.active_submission_id or 0)
        if not submissao:
            usuario.bot_state = EstadoBot.PARADO.value
            usuario.active_submission_id = None
            self.db.commit()
            return "Perdi a submissão no meio do caminho. Toca em Nova atividade de novo."

        regra = self._pegar_regra_principal(submissao.category_id)
        valor, sufixo = self._extrair_numero(texto)
        if valor is None:
            return "Não consegui ler esse valor. Manda algo como 1, 2, 3.5 ou 10h."

        if valor <= 0:
            return "Esse valor precisa ser maior que zero."

        if regra and regra.rule_type == TipoRegra.POR_UNIDADE:
            if sufixo in {"h", "hora", "horas"}:
                return self._texto_erro_unidade(regra)
            submissao.declared_quantity = valor
            submissao.declared_hours = None
        else:
            if sufixo and sufixo not in {"h", "hora", "horas"}:
                return "Para essa categoria eu preciso da carga horária. Pode mandar algo como 10, 10.5 ou 10h."
            submissao.declared_hours = valor
            submissao.declared_quantity = None

        usuario.bot_state = EstadoBot.AGUARDANDO_COMPROVANTE.value
        self.db.commit()
        return "Perfeito. Agora me manda o comprovante em PDF ou imagem."

    def _lidar_com_midias(self, usuario: Usuario, mensagem: dict) -> str:
        submissao = self._pegar_submissao_selecionada(usuario)
        if not submissao:
            return "Recebi o arquivo, mas você ainda não escolheu uma atividade. Toca em Nova atividade primeiro."

        if usuario.active_submission_id != submissao.id:
            usuario.active_submission_id = submissao.id
            self.db.commit()

        submissao = self.servico_submissoes.pegar_submissao(submissao.id)
        if not submissao or submissao.user_id != usuario.id:
            return "Não achei sua atividade aberta. Toca em Nova atividade de novo."

        if usuario.bot_state not in {EstadoBot.AGUARDANDO_COMPROVANTE.value, EstadoBot.PARADO.value}:
            return "Antes do comprovante eu preciso fechar título e medida da atividade."

        try:
            nome_arquivo, tipo_mime, file_id = self._extrair_dados_arquivo(mensagem)
            info_arquivo = self.cliente_telegram.buscar_arquivo(file_id)
            caminho_arquivo = info_arquivo.get("file_path")
            if not caminho_arquivo:
                raise ErroDominio("O Telegram não mandou o caminho do arquivo.")
            conteudo = self.cliente_telegram.baixar_arquivo(caminho_arquivo)
            atualizada = self.servico_submissoes.adicionar_comprovante_por_bytes(
                submissao.id,
                nome_arquivo=nome_arquivo,
                tipo_mime=tipo_mime,
                conteudo=conteudo,
            )
        except ErroDominio as erro:
            return str(erro)

        return self._mensagem_resumo_submissao(
            atualizada,
            cabecalho="Recebi o comprovante.",
            incluir_regra=True,
            incluir_nota=True,
        )

    def _listar_comprovantes(self, usuario: Usuario) -> tuple[str, dict | None]:
        submissao = self._pegar_submissao_selecionada(usuario)
        if not submissao:
            return "Não achei nenhuma atividade sua ainda. Toca em Nova atividade para começar.", None

        if usuario.active_submission_id != submissao.id:
            usuario.active_submission_id = submissao.id
            usuario.bot_state = EstadoBot.PARADO.value
            self.db.commit()

        submissao = self.servico_submissoes.pegar_submissao(submissao.id)
        if not submissao or submissao.user_id != usuario.id:
            return "Não achei a atividade selecionada.", None

        comprovantes = submissao.evidence_files
        if not comprovantes:
            return "Ainda não tem comprovante anexado nessa atividade.", self._acoes_submissao_inline(usuario)

        linhas = [f"Comprovantes da atividade #{submissao.id} - {submissao.title}:"]
        for comprovante in comprovantes:
            linhas.append(f"- {comprovante.id}: {comprovante.original_filename}")
        linhas.append("Toca no botão do arquivo que eu removo na hora.")
        return "\n".join(linhas), self._teclado_comprovantes(submissao.id, comprovantes)

    def _remover_comprovante_por_botao(self, usuario: Usuario, submissao_id: int, comprovante_id: int) -> str:
        submissao = self.servico_submissoes.pegar_submissao(submissao_id)
        if not submissao or submissao.user_id != usuario.id:
            return "Não achei essa atividade."

        atualizada = self.servico_submissoes.remover_comprovante(submissao_id, comprovante_id)
        return self._mensagem_resumo_submissao(
            atualizada,
            cabecalho="Pronto. Removi esse comprovante.",
            incluir_regra=False,
            incluir_nota=True,
        )

    def _finalizar_submissao(self, usuario: Usuario) -> str:
        if not usuario.active_submission_id:
            return "Não tem atividade aberta para finalizar."

        rascunho = self.servico_submissoes.pegar_submissao(usuario.active_submission_id)
        if not rascunho:
            usuario.bot_state = EstadoBot.PARADO.value
            usuario.active_submission_id = None
            self.db.commit()
            return "Perdi a atividade aberta. Toca em Nova atividade de novo."

        rascunho.status = StatusSubmissao.ENVIADA
        finalizada = self.servico_submissoes.avaliar_submissao(usuario.active_submission_id)
        usuario = self.repositorio_usuarios.pegar(usuario.id) or usuario
        usuario.bot_state = EstadoBot.PARADO.value
        usuario.active_submission_id = finalizada.id
        self.db.commit()
        return self._mensagem_resumo_submissao(
            finalizada,
            cabecalho="Atividade enviada.",
            incluir_regra=True,
            incluir_nota=True,
        )

    def _cancelar_fluxo(self, usuario: Usuario) -> str:
        usuario.bot_state = EstadoBot.PARADO.value
        usuario.active_submission_id = None
        self.db.commit()
        return "Cancelei o fluxo por aqui. Quando quiser, toca em Nova atividade."

    def _minhas_atividades(self, usuario: Usuario) -> tuple[str, dict | None]:
        submissoes = self.servico_submissoes.listar_submissoes_do_usuario(usuario.id)
        if not submissoes:
            return "Você ainda não tem nenhuma atividade cadastrada.", None

        usuario.active_submission_id = submissoes[0].id
        usuario.bot_state = EstadoBot.PARADO.value
        self.db.commit()

        linhas = ["Suas atividades:"]
        for submissao in submissoes[:10]:
            estimativa = self._formatar_horas(submissao.estimated_hours)
            linhas.append(
                f"- #{submissao.id} {submissao.title} | {submissao.category_name or 'Sem categoria'} | "
                f"{self._rotulo_status(submissao.status)} | {estimativa}"
            )
        linhas.append("Toca em um botão abaixo para abrir uma atividade.")
        return "\n".join(linhas), self._teclado_atividades(submissoes[:10])

    def _resumo(self, usuario_id: int) -> str:
        resumo = self.servico_usuarios.pegar_resumo(usuario_id)
        linhas = [
            f"Você tem {self._formatar_horas(resumo.total_estimated_hours)} estimadas.",
            f"A meta oficial é {self._formatar_horas(resumo.required_hours)}.",
            f"Ainda faltam {self._formatar_horas(resumo.remaining_hours)}.",
        ]
        linhas.extend(f"- {categoria.category_name}: {self._formatar_horas(categoria.total_hours)}" for categoria in resumo.categories)
        return "\n".join(linhas)

    def _regras(self) -> str:
        regras = self.repositorio_regras.list_all()
        if not regras:
            return "Ainda não tem regra cadastrada."
        linhas = ["Regras oficiais carregadas:"]
        for regra in regras:
            linhas.append(f"- {regra.category.name}: {self._resumo_regra(regra)}")
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
        linhas.append([{"text": TEXTO_BOTAO_AJUDA_CATEGORIA, "callback_data": "ajuda_categorias"}])
        return {"inline_keyboard": linhas}

    def _teclado_comprovantes(self, submissao_id: int, comprovantes: list) -> dict:
        linhas = [
            [{"text": f"Remover {comprovante.original_filename}", "callback_data": f"remover:{submissao_id}:{comprovante.id}"}]
            for comprovante in comprovantes
        ]
        linhas.append([{"text": "Finalizar envio", "callback_data": "finalizar_envio"}])
        return {"inline_keyboard": linhas}

    @staticmethod
    def _teclado_atividades(submissoes: list[Submissao]) -> dict:
        linhas = [
            [{"text": f"#{submissao.id} - {submissao.title[:24]}", "callback_data": f"atividade:{submissao.id}"}]
            for submissao in submissoes
        ]
        return {"inline_keyboard": linhas}

    def _teclado_medida_do_usuario(self, usuario: Usuario) -> dict | None:
        if usuario.bot_state != EstadoBot.AGUARDANDO_NUMERO.value or not usuario.active_submission_id:
            return None
        submissao = self.servico_submissoes.pegar_submissao(usuario.active_submission_id)
        if not submissao:
            return None
        regra = self._pegar_regra_principal(submissao.category_id)
        return self._teclado_medida(submissao, regra)

    def _teclado_medida(self, submissao: Submissao, regra: Regra | None) -> dict | None:
        if not regra:
            return None

        sugestoes: list[tuple[str, str]] = []
        if submissao.category_code == "CURSOS_CC_EXTERNOS":
            sugestoes = [("20h", "20"), ("40h", "40"), ("60h", "60")]
        elif regra.quantity_unit in {
            UnidadeQuantidade.EVENTO,
            UnidadeQuantidade.APRESENTACAO,
            UnidadeQuantidade.ETAPA,
            UnidadeQuantidade.PREMIACAO,
            UnidadeQuantidade.DIA,
        }:
            sugestoes = [("1", "1"), ("2", "2"), ("3", "3")]
        elif regra.quantity_unit == UnidadeQuantidade.MES:
            minimo = int(regra.minimum_quantity or 1)
            sugestoes = [(str(minimo), str(minimo)), ("6", "6"), ("12", "12")]
        elif regra.quantity_unit == UnidadeQuantidade.SEMESTRE:
            sugestoes = [("1", "1"), ("2", "2")]

        if not sugestoes:
            return None

        return {
            "inline_keyboard": [
                [{"text": f"Sugerir {rotulo}", "callback_data": f"valor:{valor}"} for rotulo, valor in sugestoes]
            ]
        }

    def _acoes_submissao_inline(self, usuario: Usuario) -> dict | None:
        submissao = self._pegar_submissao_selecionada(usuario)
        if not submissao:
            return None
        linhas = [[{"text": "Ver comprovantes", "callback_data": "ver_comprovantes"}]]
        if usuario.bot_state == EstadoBot.AGUARDANDO_COMPROVANTE.value:
            linhas.append([{"text": "Finalizar envio", "callback_data": "finalizar_envio"}])
        else:
            linhas.append([{"text": "Nova atividade", "callback_data": "nova_atividade"}])
        return {"inline_keyboard": linhas}

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

        raise ErroDominio("Não achei um arquivo válido nessa mensagem.")

    @staticmethod
    def _extrair_numero(texto: str) -> tuple[float | None, str]:
        correspondencia = re.fullmatch(r"\s*(-?\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)?\s*", texto.strip())
        if not correspondencia:
            return None, ""
        valor = float(correspondencia.group(1).replace(",", "."))
        sufixo = (correspondencia.group(2) or "").lower()
        return valor, sufixo

    def _texto_pedir_medida(self, submissao: Submissao, regra: Regra | None) -> str:
        if not regra:
            return "Agora me manda o número que essa atividade precisa."

        if submissao.category_code == "OUVINTE_EVENTOS":
            return (
                f"Perfeito. Nessa categoria eu conto por evento: {self._resumo_regra(regra)}.\n"
                "Agora me diz: esse comprovante cobre quantos eventos como ouvinte?\n"
                "Se foi uma palestra ou um evento só, normalmente a resposta é 1."
            )
        if submissao.category_code == "APRESENTACAO_EVENTOS":
            return (
                f"Perfeito. Nessa categoria eu conto por apresentação: {self._resumo_regra(regra)}.\n"
                "Agora me diz: esse comprovante cobre quantas apresentações?"
            )
        if submissao.category_code == "COMPETICOES":
            return (
                f"Perfeito. Nessa categoria eu conto por etapa: {self._resumo_regra(regra)}.\n"
                "Agora me diz: esse comprovante cobre quantas etapas da competição?"
            )
        if submissao.category_code == "PREMIACOES":
            return (
                f"Perfeito. Nessa categoria eu conto por premiação: {self._resumo_regra(regra)}.\n"
                "Agora me diz: esse comprovante cobre quantas premiações ou menções?"
            )
        if submissao.category_code == "ORGANIZACAO_EVENTOS":
            return (
                f"Perfeito. Nessa categoria eu conto por evento organizado: {self._resumo_regra(regra)}.\n"
                "Agora me diz: esse comprovante cobre quantos eventos?"
            )
        if submissao.category_code == "MESARIO":
            return (
                f"Perfeito. Nessa categoria eu conto por dia de atuação: {self._resumo_regra(regra)}.\n"
                "Agora me diz: esse comprovante cobre quantos dias como mesário?"
            )
        if submissao.category_code == "CURSOS_CC_EXTERNOS":
            return (
                f"Perfeito. Nessa categoria eu uso a carga horária do curso e aproveito 50%: {self._resumo_regra(regra)}.\n"
                "Agora me manda a carga horária total do curso. Pode ser 20, 40, 60 ou 40h."
            )
        if submissao.category_code == "CURSOS_IDIOMAS":
            return (
                f"Perfeito. Nessa categoria eu conto por semestre: {self._resumo_regra(regra)}.\n"
                "Agora me diz quantos semestres esse comprovante cobre."
            )

        if regra.rule_type in {TipoRegra.PERCENTUAL_DAS_HORAS, TipoRegra.HORAS_DECLARADAS}:
            return (
                f"Perfeito. Nessa categoria eu uso a carga horária do certificado: {self._resumo_regra(regra)}.\n"
                "Agora me manda a carga horária total. Pode ser 10, 10.5 ou 10h."
            )

        if regra.quantity_unit == UnidadeQuantidade.MES:
            return f"Perfeito. Nessa categoria eu conto por mês: {self._resumo_regra(regra)}.\nAgora me diz quantos meses esse comprovante cobre."
        if regra.quantity_unit == UnidadeQuantidade.SEMESTRE:
            return f"Perfeito. Nessa categoria eu conto por semestre: {self._resumo_regra(regra)}.\nAgora me diz quantos semestres esse comprovante cobre."
        if regra.quantity_unit == UnidadeQuantidade.EVENTO:
            return f"Perfeito. Nessa categoria eu conto por evento: {self._resumo_regra(regra)}.\nAgora me diz quantos eventos esse comprovante cobre."
        if regra.quantity_unit == UnidadeQuantidade.APRESENTACAO:
            return f"Perfeito. Nessa categoria eu conto por apresentação: {self._resumo_regra(regra)}.\nAgora me diz quantas apresentações esse comprovante cobre."
        if regra.quantity_unit == UnidadeQuantidade.ETAPA:
            return f"Perfeito. Nessa categoria eu conto por etapa: {self._resumo_regra(regra)}.\nAgora me diz quantas etapas esse comprovante cobre."
        if regra.quantity_unit == UnidadeQuantidade.PREMIACAO:
            return f"Perfeito. Nessa categoria eu conto por premiação: {self._resumo_regra(regra)}.\nAgora me diz quantas premiações esse comprovante cobre."
        if regra.quantity_unit == UnidadeQuantidade.DIA:
            return f"Perfeito. Nessa categoria eu conto por dia: {self._resumo_regra(regra)}.\nAgora me diz quantos dias esse comprovante cobre."

        return f"Perfeito. Nessa categoria a regra é: {self._resumo_regra(regra)}.\nAgora me manda o número que essa atividade precisa."

    def _texto_erro_unidade(self, regra: Regra) -> str:
        return {
            UnidadeQuantidade.MES: "Para essa categoria eu não uso horas. A regra do IC conta por mês. Me diz quantos meses foram.",
            UnidadeQuantidade.EVENTO: "Para essa categoria eu não uso horas do evento. A regra do IC conta por evento. Me diz quantos eventos foram.",
            UnidadeQuantidade.APRESENTACAO: "Para essa categoria eu não uso horas. A regra do IC conta por apresentação. Me diz quantas apresentações foram.",
            UnidadeQuantidade.ETAPA: "Para essa categoria eu não uso horas. A regra do IC conta por etapa. Me diz quantas etapas foram.",
            UnidadeQuantidade.PREMIACAO: "Para essa categoria eu não uso horas. A regra do IC conta por premiação. Me diz quantas premiações foram.",
            UnidadeQuantidade.DIA: "Para essa categoria eu não uso horas. A regra do IC conta por dia. Me diz quantos dias foram.",
            UnidadeQuantidade.SEMESTRE: "Para essa categoria eu não uso horas. A regra do IC conta por semestre. Me diz quantos semestres foram.",
            UnidadeQuantidade.CURSO: "Para essa categoria eu não uso horas diretamente nesse campo. Me diz quantos cursos quer lançar.",
        }.get(regra.quantity_unit, "Para essa categoria eu não uso horas nesse campo. Me manda o número que a regra pede.")

    @staticmethod
    def _rotulo_status(status: StatusSubmissao) -> str:
        return {
            StatusSubmissao.RASCUNHO: "rascunho",
            StatusSubmissao.ENVIADA: "enviada",
            StatusSubmissao.PRECISA_REVISAO: "precisa de revisão",
            StatusSubmissao.ESTIMATIVA_APROVADA: "estimativa aprovada",
            StatusSubmissao.ESTIMATIVA_REJEITADA: "estimativa rejeitada",
        }.get(status, status.value.replace("_", " "))

    @staticmethod
    def _formatar_horas(valor: float | None) -> str:
        if valor is None:
            return "sem estimativa"
        return f"{valor:.2f}h".replace(".", ",")

    def _mensagem_resumo_submissao(
        self,
        submissao: Submissao,
        *,
        cabecalho: str,
        incluir_regra: bool,
        incluir_nota: bool,
    ) -> str:
        linhas = [
            cabecalho,
            "",
            f"Atividade: #{submissao.id} - {submissao.title}",
            f"Categoria: {submissao.category_name or 'Sem categoria'}",
            f"Status: {self._rotulo_status(submissao.status)}",
            f"Valor informado: {self._resumo_valor_informado(submissao)}",
            f"Horas estimadas: {self._formatar_horas(submissao.estimated_hours)}",
        ]
        regra = self._pegar_regra_principal(submissao.category_id)
        if incluir_regra and regra:
            linhas.append(f"Regra aplicada: {self._resumo_regra(regra)}")
        if incluir_nota and submissao.review_notes:
            linhas.append(f"Observação: {submissao.review_notes}")
        if submissao.evidence_files:
            linhas.append("")
            linhas.append("Se esse não era o comprovante certo, toca em Ver comprovantes para remover.")
        return "\n".join(linhas)

    def _resumo_regra(self, regra: Regra) -> str:
        partes: list[str] = []
        if regra.rule_type == TipoRegra.POR_UNIDADE and regra.hours_per_unit is not None:
            partes.append(f"{regra.hours_per_unit:g}h por {self._rotulo_unidade_curta(regra)}")
        elif regra.rule_type == TipoRegra.PERCENTUAL_DAS_HORAS and regra.percentage_multiplier is not None:
            percentual = int(regra.percentage_multiplier * 100)
            partes.append(f"{percentual}% da carga horária")
        elif regra.rule_type == TipoRegra.HORAS_DECLARADAS:
            partes.append("horas declaradas")
        elif regra.rule_type == TipoRegra.HORAS_FIXAS and regra.fixed_hours is not None:
            partes.append(f"{regra.fixed_hours:g}h fixas")

        if regra.minimum_quantity is not None:
            partes.append(f"mínimo de {regra.minimum_quantity:g} {self._rotulo_unidade_curta(regra)}")
        if regra.max_hours_per_category is not None:
            partes.append(f"teto de {regra.max_hours_per_category:g}h")
        return ", ".join(partes) if partes else regra.short_description

    @staticmethod
    def _rotulo_unidade_curta(regra: Regra) -> str:
        if regra.quantity_unit is None:
            return "unidade"
        return {
            UnidadeQuantidade.MES: "mês",
            UnidadeQuantidade.EVENTO: "evento",
            UnidadeQuantidade.APRESENTACAO: "apresentação",
            UnidadeQuantidade.ETAPA: "etapa",
            UnidadeQuantidade.PREMIACAO: "premiação",
            UnidadeQuantidade.DIA: "dia",
            UnidadeQuantidade.SEMESTRE: "semestre",
            UnidadeQuantidade.CURSO: "curso",
        }.get(regra.quantity_unit, "unidade")

    def _resumo_valor_informado(self, submissao: Submissao) -> str:
        regra = self._pegar_regra_principal(submissao.category_id)
        if submissao.declared_hours is not None:
            return self._formatar_horas(submissao.declared_hours)
        if submissao.declared_quantity is None:
            return "não informado"
        if not regra or regra.quantity_unit is None:
            return f"{submissao.declared_quantity:g} unidade(s)"
        return f"{submissao.declared_quantity:g} {self._rotulo_unidade_curta(regra)}(s)"

    def _pegar_submissao_selecionada(self, usuario: Usuario) -> Submissao | None:
        if usuario.active_submission_id:
            submissao = self.servico_submissoes.pegar_submissao(usuario.active_submission_id)
            if submissao and submissao.user_id == usuario.id:
                return submissao

        submissoes = self.servico_submissoes.listar_submissoes_do_usuario(usuario.id)
        return submissoes[0] if submissoes else None

    @staticmethod
    def _texto_ajuda_categorias() -> str:
        return (
            "Como escolher a categoria:\n"
            "• Palestra, seminário, colóquio, simpósio, congresso, feira, SIAC ou JIC em que você participou como ouvinte: "
            "Ouvinte em Eventos.\n"
            "• Trabalho apresentado em evento: Apresentação de Trabalhos.\n"
            "• Curso externo da área de computação: Cursos Externos de Ciência da Computação.\n"
            "• Curso de idioma: Cursos de Idiomas.\n"
            "• Estágio: Estágio.\n\n"
            "Se ficar na dúvida, escolhe a categoria mais próxima e depois confere em Regras."
        )

    @staticmethod
    def _explicacao_categoria(codigo_categoria: str) -> str:
        explicacoes = {
            "OUVINTE_EVENTOS": (
                "Use essa categoria para palestra, seminário, congresso, simpósio, feira, colóquio e eventos parecidos "
                "em que você participou como ouvinte."
            ),
            "APRESENTACAO_EVENTOS": (
                "Use essa categoria quando você apresentou trabalho em evento acadêmico ou científico."
            ),
            "CURSOS_CC_EXTERNOS": (
                "Use essa categoria para cursos externos da área de computação em que o certificado informa a carga horária."
            ),
            "CURSOS_IDIOMAS": (
                "Use essa categoria para cursos de idioma com comprovante do período cursado."
            ),
            "ESTAGIO": (
                "Use essa categoria para estágio feito durante a graduação, com a documentação exigida pela coordenação."
            ),
        }
        return explicacoes.get(
            codigo_categoria,
            "Se essa categoria for a certa, eu já vou te pedir exatamente o dado que a regra dela usa."
        )

    @staticmethod
    def _eh_inicio(texto: str) -> bool:
        return texto.startswith("/start") or texto == "Começar"

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

