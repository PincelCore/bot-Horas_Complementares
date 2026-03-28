from io import BytesIO

from sqlalchemy import select

from app.models import EventoAuditoria


def pegar_categoria(cliente_api, codigo: str) -> dict:
    resposta = cliente_api.get("/categories")
    categorias = resposta.json()
    return next(item for item in categorias if item["code"] == codigo)


def pdf_certificado_bytes(nome: str = "Davi") -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<<>>\nstream\n"
        + f"(CERTIFICADO de participacao. {nome}. carga horaria 12 horas. evento academico UFRJ.)\n".encode("latin-1")
        + b"endstream\nendobj\n%%EOF"
    )


def pdf_invalido_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<<>>\nstream\n"
        b"(BOLETO bancario. Pix copia e cola. Nota fiscal e comprovante de residencia.)\n"
        b"endstream\nendobj\n%%EOF"
    )


def test_cria_submissao_envia_comprovante_e_fecha_resumo(client):
    resposta_usuario = client.post("/users", json={"full_name": "Davi"})
    usuario_id = resposta_usuario.json()["id"]
    categoria = pegar_categoria(client, "ESTAGIO")
    assert categoria["max_hours"] == 54

    resposta_submissao = client.post(
        "/submissions",
        json={
            "user_id": usuario_id,
            "category_code": categoria["code"],
            "title": "Estagio em laboratorio",
            "description": "Estagio de 4 meses",
            "declared_quantity": 4,
        },
    )
    assert resposta_submissao.status_code == 201
    submissao_id = resposta_submissao.json()["id"]
    assert resposta_submissao.json()["status"] == "needs_review"

    resposta_upload = client.post(
        f"/submissions/{submissao_id}/evidences",
        files={"file": ("certificado.pdf", BytesIO(pdf_certificado_bytes()), "application/pdf")},
    )
    assert resposta_upload.status_code == 200
    assert resposta_upload.json()["status"] == "approved_estimate"
    assert resposta_upload.json()["estimated_hours"] == 36

    resposta_resumo = client.get(f"/users/{usuario_id}/summary")
    assert resposta_resumo.status_code == 200
    assert resposta_resumo.json()["total_estimated_hours"] == 36
    assert resposta_resumo.json()["remaining_hours"] == 54


def test_regra_percentual_para_curso_externo(client):
    resposta_usuario = client.post("/users", json={"full_name": "Davi"})
    usuario_id = resposta_usuario.json()["id"]
    categoria = pegar_categoria(client, "CURSOS_CC_EXTERNOS")

    resposta_submissao = client.post(
        "/submissions",
        json={
            "user_id": usuario_id,
            "category_code": categoria["code"],
            "title": "Curso externo",
            "description": "Curso de 40h",
            "declared_hours": 40,
        },
    )
    submissao_id = resposta_submissao.json()["id"]

    resposta_upload = client.post(
        f"/submissions/{submissao_id}/evidences",
        files={"file": ("certificado.pdf", BytesIO(pdf_certificado_bytes()), "application/pdf")},
    )
    assert resposta_upload.status_code == 200
    assert resposta_upload.json()["estimated_hours"] == 20


def test_rejeita_tipo_de_arquivo_invalido(client):
    resposta_usuario = client.post("/users", json={"full_name": "Davi"})
    usuario_id = resposta_usuario.json()["id"]
    categoria = pegar_categoria(client, "ESTAGIO")
    resposta_submissao = client.post(
        "/submissions",
        json={"user_id": usuario_id, "category_code": categoria["code"], "title": "Estagio", "declared_quantity": 4},
    )
    submissao_id = resposta_submissao.json()["id"]

    resposta_upload = client.post(
        f"/submissions/{submissao_id}/evidences",
        files={"file": ("notes.txt", BytesIO(b"text"), "text/plain")},
    )
    assert resposta_upload.status_code == 400


def test_remover_comprovante_recalcula_submissao(client):
    resposta_usuario = client.post("/users", json={"full_name": "Davi"})
    usuario_id = resposta_usuario.json()["id"]
    categoria = pegar_categoria(client, "ESTAGIO")

    resposta_submissao = client.post(
        "/submissions",
        json={
            "user_id": usuario_id,
            "category_code": categoria["code"],
            "title": "Estagio",
            "description": "Estagio de 4 meses",
            "declared_quantity": 4,
        },
    )
    submissao_id = resposta_submissao.json()["id"]

    resposta_upload = client.post(
        f"/submissions/{submissao_id}/evidences",
        files={"file": ("certificado.pdf", BytesIO(pdf_certificado_bytes()), "application/pdf")},
    )
    comprovante_id = resposta_upload.json()["evidences"][0]["id"]

    resposta_remocao = client.delete(f"/submissions/{submissao_id}/evidences/{comprovante_id}")

    assert resposta_remocao.status_code == 200
    assert resposta_remocao.json()["status"] == "needs_review"
    assert resposta_remocao.json()["estimated_hours"] is None
    assert resposta_remocao.json()["evidences"] == []


def test_remover_submissao_apaga_registro_e_lista_do_usuario(client, db):
    resposta_usuario = client.post("/users", json={"full_name": "Davi"})
    usuario_id = resposta_usuario.json()["id"]
    categoria = pegar_categoria(client, "ESTAGIO")

    resposta_submissao = client.post(
        "/submissions",
        json={
            "user_id": usuario_id,
            "category_code": categoria["code"],
            "title": "Estagio",
            "description": "Estagio de 4 meses",
            "declared_quantity": 4,
        },
    )
    submissao_id = resposta_submissao.json()["id"]

    resposta_upload = client.post(
        f"/submissions/{submissao_id}/evidences",
        files={"file": ("certificado.pdf", BytesIO(pdf_certificado_bytes()), "application/pdf")},
    )
    assert resposta_upload.status_code == 200

    resposta_remocao = client.delete(f"/submissions/{submissao_id}")

    assert resposta_remocao.status_code == 204
    assert client.get(f"/submissions/{submissao_id}").status_code == 404
    assert client.get(f"/users/{usuario_id}/submissions").json() == []

    eventos = list(
        db.scalars(
            select(EventoAuditoria).where(EventoAuditoria.event_type.in_(["submissao.criada", "submissao.removida"]))
        ).all()
    )

    assert any(evento.event_type == "submissao.removida" and evento.submission_id is None for evento in eventos)
    assert not list(db.scalars(select(EventoAuditoria).where(EventoAuditoria.submission_id == submissao_id)).all())


def test_rejeita_pdf_que_parece_documento_irrelevante(client):
    resposta_usuario = client.post("/users", json={"full_name": "Davi"})
    usuario_id = resposta_usuario.json()["id"]
    categoria = pegar_categoria(client, "ESTAGIO")

    resposta_submissao = client.post(
        "/submissions",
        json={
            "user_id": usuario_id,
            "category_code": categoria["code"],
            "title": "Estagio",
            "description": "Estagio de 4 meses",
            "declared_quantity": 4,
        },
    )
    submissao_id = resposta_submissao.json()["id"]

    resposta_upload = client.post(
        f"/submissions/{submissao_id}/evidences",
        files={"file": ("boleto.pdf", BytesIO(pdf_invalido_bytes()), "application/pdf")},
    )

    assert resposta_upload.status_code == 400
    assert "não parece um certificado" in resposta_upload.json()["detail"].lower()

