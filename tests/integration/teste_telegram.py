from app.bot.cliente_telegram import ClienteTelegram


def pegar_categoria(cliente_api, codigo: str) -> dict:
    resposta = cliente_api.get("/categories")
    return next(item for item in resposta.json() if item["code"] == codigo)


def test_fluxo_do_telegram_com_botoes_e_validacoes(client, monkeypatch):
    categoria = pegar_categoria(client, "ESTAGIO")
    mensagens_enviadas: list[dict] = []

    def falso_enviar(self, chat_id, texto, marcacao=None):
        mensagens_enviadas.append({"chat_id": chat_id, "texto": texto, "marcacao": marcacao})

    monkeypatch.setattr(ClienteTelegram, "enviar_mensagem", falso_enviar)
    monkeypatch.setattr(ClienteTelegram, "responder_callback", lambda self, callback_id, texto=None: None)

    resposta_inicio = client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 777}, "from": {"first_name": "Davi"}, "text": "/start"}},
    )
    assert resposta_inicio.status_code == 200
    assert "Fechou, Davi" in resposta_inicio.json()["message"]
    assert any(
        botao["text"] == "Nova atividade"
        for linha in mensagens_enviadas[-1]["marcacao"]["keyboard"]
        for botao in linha
    )

    resposta_nova = client.post("/telegram/webhook", json={"message": {"chat": {"id": 777}, "text": "Nova atividade"}})
    assert "escolhe a categoria" in resposta_nova.json()["message"].lower()
    assert any(
        botao["callback_data"] == f"categoria:{categoria['code']}"
        for linha in mensagens_enviadas[-1]["marcacao"]["inline_keyboard"]
        for botao in linha
    )

    resposta_categoria = client.post(
        "/telegram/webhook",
        json={
            "callback_query": {"id": "cb-1", "data": f"categoria:{categoria['code']}", "message": {"chat": {"id": 777}}}
        },
    )
    assert "Categoria escolhida" in resposta_categoria.json()["message"]

    resposta_titulo_curto = client.post("/telegram/webhook", json={"message": {"chat": {"id": 777}, "text": "Oi"}})
    assert "Titulo muito curtinho" in resposta_titulo_curto.json()["message"]

    resposta_titulo = client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 777}, "text": "Estagio no laboratorio de IA"}},
    )
    assert "Agora manda um numero" in resposta_titulo.json()["message"]

    resposta_numero_invalido = client.post("/telegram/webhook", json={"message": {"chat": {"id": 777}, "text": "quatro"}})
    assert "Esse numero nao rolou" in resposta_numero_invalido.json()["message"]

    resposta_numero_negativo = client.post("/telegram/webhook", json={"message": {"chat": {"id": 777}, "text": "-1"}})
    assert "maior que zero" in resposta_numero_negativo.json()["message"]

    resposta_numero = client.post("/telegram/webhook", json={"message": {"chat": {"id": 777}, "text": "4"}})
    assert "Agora so me manda o certificado" in resposta_numero.json()["message"]


def test_telegram_exige_start(client, monkeypatch):
    monkeypatch.setattr(ClienteTelegram, "enviar_mensagem", lambda self, chat_id, texto, marcacao=None: None)

    resposta = client.post("/telegram/webhook", json={"message": {"chat": {"id": 999}, "text": "/resumo"}})
    assert resposta.status_code == 200
    assert "Manda um /start" in resposta.json()["message"]


def test_upload_listagem_e_remocao_por_botoes(client, monkeypatch):
    categoria = pegar_categoria(client, "ESTAGIO")
    mensagens_enviadas: list[dict] = []

    def falso_enviar(self, chat_id, texto, marcacao=None):
        mensagens_enviadas.append({"chat_id": chat_id, "texto": texto, "marcacao": marcacao})

    monkeypatch.setattr(ClienteTelegram, "enviar_mensagem", falso_enviar)
    monkeypatch.setattr(ClienteTelegram, "responder_callback", lambda self, callback_id, texto=None: None)
    monkeypatch.setattr(ClienteTelegram, "buscar_arquivo", lambda self, file_id: {"file_path": f"docs/{file_id}.pdf"})
    monkeypatch.setattr(ClienteTelegram, "baixar_arquivo", lambda self, caminho_arquivo: b"fake pdf content")

    client.post("/telegram/webhook", json={"message": {"chat": {"id": 700}, "from": {"first_name": "Davi"}, "text": "/start"}})
    client.post("/telegram/webhook", json={"message": {"chat": {"id": 700}, "text": "Nova atividade"}})
    client.post(
        "/telegram/webhook",
        json={
            "callback_query": {"id": "cb-10", "data": f"categoria:{categoria['code']}", "message": {"chat": {"id": 700}}}
        },
    )
    client.post("/telegram/webhook", json={"message": {"chat": {"id": 700}, "text": "Estagio no laboratorio"}})
    client.post("/telegram/webhook", json={"message": {"chat": {"id": 700}, "text": "4"}})

    resposta_upload = client.post(
        "/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 700},
                "document": {
                    "file_id": "abc123",
                    "file_unique_id": "unique123",
                    "file_name": "certificado.pdf",
                    "mime_type": "application/pdf",
                },
            }
        },
    )
    assert resposta_upload.status_code == 200
    assert "Certificado anexado" in resposta_upload.json()["message"]

    resposta_comprovantes = client.post(
        "/telegram/webhook",
        json={"callback_query": {"id": "cb-11", "data": "ver_comprovantes", "message": {"chat": {"id": 700}}}},
    )
    assert "certificado.pdf" in resposta_comprovantes.json()["message"]
    assert any(
        botao["callback_data"].startswith("remover:1:")
        for linha in mensagens_enviadas[-1]["marcacao"]["inline_keyboard"]
        for botao in linha
    )

    comprovante_id = client.get("/submissions/1").json()["evidences"][0]["id"]
    resposta_remocao = client.post(
        "/telegram/webhook",
        json={
            "callback_query": {
                "id": "cb-12",
                "data": f"remover:1:{comprovante_id}",
                "message": {"chat": {"id": 700}},
            }
        },
    )
    assert "removi o comprovante" in resposta_remocao.json()["message"]

