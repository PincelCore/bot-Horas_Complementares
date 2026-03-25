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
    assert "ouvinte em eventos" in resposta_nova.json()["message"].lower()
    assert any(
        botao["callback_data"] == f"categoria:{categoria['code']}"
        for linha in mensagens_enviadas[-1]["marcacao"]["inline_keyboard"]
        for botao in linha
    )
    assert any(
        botao["callback_data"] == "ajuda_categorias"
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
    assert "Como essa categoria funciona" in resposta_categoria.json()["message"]

    resposta_titulo_curto = client.post("/telegram/webhook", json={"message": {"chat": {"id": 777}, "text": "Oi"}})
    assert "Título muito curtinho" in resposta_titulo_curto.json()["message"]

    resposta_titulo = client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 777}, "text": "Estagio no laboratorio de IA"}},
    )
    assert "conto por mês" in resposta_titulo.json()["message"]
    assert "quantos meses" in resposta_titulo.json()["message"]
    assert any(
        botao["callback_data"] == "valor:3"
        for linha in mensagens_enviadas[-1]["marcacao"]["inline_keyboard"]
        for botao in linha
    )

    resposta_numero_invalido = client.post("/telegram/webhook", json={"message": {"chat": {"id": 777}, "text": "quatro"}})
    assert "Não consegui ler esse valor" in resposta_numero_invalido.json()["message"]

    resposta_numero_negativo = client.post("/telegram/webhook", json={"message": {"chat": {"id": 777}, "text": "-1"}})
    assert "maior que zero" in resposta_numero_negativo.json()["message"]

    resposta_numero = client.post("/telegram/webhook", json={"message": {"chat": {"id": 777}, "text": "4"}})
    assert "me manda o comprovante" in resposta_numero.json()["message"]


def test_telegram_rejeita_horas_quando_categoria_conta_por_evento(client, monkeypatch):
    categoria = pegar_categoria(client, "OUVINTE_EVENTOS")

    monkeypatch.setattr(ClienteTelegram, "enviar_mensagem", lambda self, chat_id, texto, marcacao=None: None)
    monkeypatch.setattr(ClienteTelegram, "responder_callback", lambda self, callback_id, texto=None: None)

    client.post("/telegram/webhook", json={"message": {"chat": {"id": 778}, "from": {"first_name": "Davi"}, "text": "/start"}})
    client.post("/telegram/webhook", json={"message": {"chat": {"id": 778}, "text": "Nova atividade"}})
    client.post(
        "/telegram/webhook",
        json={
            "callback_query": {"id": "cb-2", "data": f"categoria:{categoria['code']}", "message": {"chat": {"id": 778}}}
        },
    )
    client.post("/telegram/webhook", json={"message": {"chat": {"id": 778}, "text": "Feira da carreira"}})

    resposta_horas = client.post("/telegram/webhook", json={"message": {"chat": {"id": 778}, "text": "10h"}})

    assert "não uso horas do evento" in resposta_horas.json()["message"].lower()


def test_telegram_sugere_um_evento_por_padrao(client, monkeypatch):
    categoria = pegar_categoria(client, "OUVINTE_EVENTOS")
    mensagens_enviadas: list[dict] = []

    def falso_enviar(self, chat_id, texto, marcacao=None):
        mensagens_enviadas.append({"chat_id": chat_id, "texto": texto, "marcacao": marcacao})

    monkeypatch.setattr(ClienteTelegram, "enviar_mensagem", falso_enviar)
    monkeypatch.setattr(ClienteTelegram, "responder_callback", lambda self, callback_id, texto=None: None)

    client.post("/telegram/webhook", json={"message": {"chat": {"id": 781}, "from": {"first_name": "Davi"}, "text": "/start"}})
    client.post("/telegram/webhook", json={"message": {"chat": {"id": 781}, "text": "Nova atividade"}})
    client.post(
        "/telegram/webhook",
        json={
            "callback_query": {"id": "cb-evento", "data": f"categoria:{categoria['code']}", "message": {"chat": {"id": 781}}}
        },
    )

    resposta_titulo = client.post("/telegram/webhook", json={"message": {"chat": {"id": 781}, "text": "Palestra X"}})
    assert "quantos eventos como ouvinte" in resposta_titulo.json()["message"].lower()
    assert "normalmente a resposta é 1" in resposta_titulo.json()["message"].lower()
    assert any(
        botao["callback_data"] == "valor:1"
        for linha in mensagens_enviadas[-1]["marcacao"]["inline_keyboard"]
        for botao in linha
    )

    resposta_valor = client.post(
        "/telegram/webhook",
        json={"callback_query": {"id": "cb-valor", "data": "valor:1", "message": {"chat": {"id": 781}}}},
    )
    assert "me manda o comprovante" in resposta_valor.json()["message"].lower()


def test_telegram_mostra_ajuda_de_categoria(client, monkeypatch):
    categoria = pegar_categoria(client, "OUVINTE_EVENTOS")

    monkeypatch.setattr(ClienteTelegram, "enviar_mensagem", lambda self, chat_id, texto, marcacao=None: None)
    monkeypatch.setattr(ClienteTelegram, "responder_callback", lambda self, callback_id, texto=None: None)

    client.post("/telegram/webhook", json={"message": {"chat": {"id": 780}, "from": {"first_name": "Davi"}, "text": "/start"}})
    client.post("/telegram/webhook", json={"message": {"chat": {"id": 780}, "text": "Nova atividade"}})

    resposta_ajuda = client.post(
        "/telegram/webhook",
        json={"callback_query": {"id": "cb-ajuda", "data": "ajuda_categorias", "message": {"chat": {"id": 780}}}},
    )
    assert "palestra" in resposta_ajuda.json()["message"].lower()
    assert "ouvinte em eventos" in resposta_ajuda.json()["message"].lower()

    resposta_categoria = client.post(
        "/telegram/webhook",
        json={
            "callback_query": {"id": "cb-2b", "data": f"categoria:{categoria['code']}", "message": {"chat": {"id": 780}}}
        },
    )
    assert "palestra" in resposta_categoria.json()["message"].lower()


def test_telegram_explica_teto_quando_categoria_limita_horas(client, monkeypatch):
    categoria = pegar_categoria(client, "OUVINTE_EVENTOS")

    monkeypatch.setattr(ClienteTelegram, "enviar_mensagem", lambda self, chat_id, texto, marcacao=None: None)
    monkeypatch.setattr(ClienteTelegram, "responder_callback", lambda self, callback_id, texto=None: None)
    monkeypatch.setattr(ClienteTelegram, "buscar_arquivo", lambda self, file_id: {"file_path": f"docs/{file_id}.pdf"})
    monkeypatch.setattr(ClienteTelegram, "baixar_arquivo", lambda self, caminho_arquivo: b"fake pdf content")

    client.post("/telegram/webhook", json={"message": {"chat": {"id": 779}, "from": {"first_name": "Davi"}, "text": "/start"}})
    client.post("/telegram/webhook", json={"message": {"chat": {"id": 779}, "text": "Nova atividade"}})
    client.post(
        "/telegram/webhook",
        json={
            "callback_query": {"id": "cb-3", "data": f"categoria:{categoria['code']}", "message": {"chat": {"id": 779}}}
        },
    )
    client.post("/telegram/webhook", json={"message": {"chat": {"id": 779}, "text": "Feira da carreira"}})
    client.post("/telegram/webhook", json={"message": {"chat": {"id": 779}, "text": "10"}})

    resposta_upload = client.post(
        "/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 779},
                "document": {
                    "file_id": "evento10",
                    "file_unique_id": "evento10",
                    "file_name": "evento.pdf",
                    "mime_type": "application/pdf",
                },
            }
        },
    )

    assert "teto oficial dessa categoria é 18,00h" in resposta_upload.json()["message"].lower()
    assert "valor informado: 10 evento(s)" in resposta_upload.json()["message"].lower()


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
    assert "Recebi o comprovante" in resposta_upload.json()["message"]
    assert "Status: estimativa aprovada" in resposta_upload.json()["message"]

    resposta_finalizar = client.post(
        "/telegram/webhook",
        json={"callback_query": {"id": "cb-11", "data": "finalizar_envio", "message": {"chat": {"id": 700}}}},
    )
    assert "Atividade enviada" in resposta_finalizar.json()["message"]
    assert any(
        botao["text"] == "Ver comprovantes"
        for linha in mensagens_enviadas[-1]["marcacao"]["inline_keyboard"]
        for botao in linha
    )

    resposta_comprovantes = client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 700}, "text": "Comprovantes"}},
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
                "id": "cb-13",
                "data": f"remover:1:{comprovante_id}",
                "message": {"chat": {"id": 700}},
            }
        },
    )
    assert "Removi esse comprovante" in resposta_remocao.json()["message"]

