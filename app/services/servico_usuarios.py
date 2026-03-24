from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.domain.enumeracoes import EstadoBot
from app.models import Usuario
from app.repositories.repositorio_submissoes import RepositorioSubmissoes
from app.repositories.repositorio_usuarios import RepositorioUsuarios
from app.schemas.usuario import ResumoHorasCategoria, ContagemStatus, UsuarioCriacao, ResumoUsuario


class ServicoUsuarios:
    HORAS_COMPLEMENTARES_OBRIGATORIAS = 90.0

    def __init__(self, db: Session):
        self.db = db
        self.repositorio_usuarios = RepositorioUsuarios(db)
        self.repositorio_submissoes = RepositorioSubmissoes(db)

    def criar_usuario(self, dados: UsuarioCriacao) -> Usuario:
        usuario = Usuario(
            full_name=dados.full_name,
            email=dados.email,
            telegram_chat_id=dados.telegram_chat_id,
            telegram_username=dados.telegram_username,
            bot_state=EstadoBot.PARADO.value,
        )
        usuario = self.repositorio_usuarios.criar(usuario)
        self.db.commit()
        return usuario

    def create_user(self, payload: UsuarioCriacao) -> Usuario:
        return self.criar_usuario(payload)

    def pegar_resumo(self, user_id: int) -> ResumoUsuario:
        submissoes = self.repositorio_submissoes.listar_por_usuario(user_id)
        totais_por_categoria: dict[tuple[str | None, str], float] = defaultdict(float)
        contagem_por_status: Counter[str] = Counter()
        horas_totais = 0.0

        for submissao in submissoes:
            nome_categoria = submissao.category.name if submissao.category else "Sem categoria"
            codigo_categoria = submissao.category.code if submissao.category else None
            chave_categoria = (codigo_categoria, nome_categoria)
            totais_por_categoria[chave_categoria] += float(submissao.estimated_hours or 0.0)
            contagem_por_status[submissao.status.value] += 1
            horas_totais += float(submissao.estimated_hours or 0.0)

        categorias = [
            ResumoHorasCategoria(category_code=codigo_categoria, category_name=nome, total_hours=horas)
            for (codigo_categoria, nome), horas in sorted(totais_por_categoria.items(), key=lambda item: item[0][1])
        ]
        status = [ContagemStatus(status=nome_status, count=quantidade) for nome_status, quantidade in sorted(contagem_por_status.items())]
        horas_restantes = max(self.HORAS_COMPLEMENTARES_OBRIGATORIAS - horas_totais, 0.0)
        return ResumoUsuario(
            user_id=user_id,
            total_estimated_hours=horas_totais,
            required_hours=self.HORAS_COMPLEMENTARES_OBRIGATORIAS,
            remaining_hours=horas_restantes,
            categories=categorias,
            statuses=status,
        )

    def get_summary(self, user_id: int) -> ResumoUsuario:
        return self.pegar_resumo(user_id)


UserService = ServicoUsuarios

