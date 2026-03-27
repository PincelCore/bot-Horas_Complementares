import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
TMP_DIR = ROOT / ".tmp"


def test_alembic_upgrade_head_funciona_em_sqlite() -> None:
    TMP_DIR.mkdir(exist_ok=True)
    banco = TMP_DIR / f"migration_test_{uuid4().hex}.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{banco.as_posix()}"

    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr or resultado.stdout

    conexao = sqlite3.connect(banco)
    try:
        tabelas = {
            nome
            for (nome,) in conexao.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        versao = conexao.execute("SELECT version_num FROM alembic_version").fetchone()
    finally:
        conexao.close()

    assert "received_documents" in tabelas
    assert versao == ("0003_received_docs",)
    banco.unlink(missing_ok=True)
