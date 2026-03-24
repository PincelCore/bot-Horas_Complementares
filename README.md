# Horas Complementares Bot

API em FastAPI com integracao Telegram para organizar comprovantes e estimar horas complementares.

O projeto sobe com seed oficial do BCC/UFRJ `2022/2` para categorias, limites e formulas de conversao de horas.

## Stack

- FastAPI
- SQLAlchemy
- SQLite no desenvolvimento
- PostgreSQL no deploy
- Alembic para migracoes

## Funcionalidades da v1

- Cadastro de usuarios e vinculo com Telegram
- Cadastro de categorias e regras de calculo de horas
- Seed oficial das regras do BCC/UFRJ
- Criacao e consulta de submissoes
- Upload de comprovantes com armazenamento em disco
- Upload de comprovantes direto pelo Telegram
- Remocao de comprovantes pela API e pelo Telegram
- Resumo consolidado por categoria e status
- Webhook Telegram com comandos e botoes clicaveis

## Execucao local

Use SQLite no desenvolvimento. O `.env.example` ja vem pronto para isso.
Mantenha o `.env` local em SQLite para desenvolver, testar no Swagger e validar o bot antes do deploy.

Se voce ja criou um `horas_bot.db` antigo antes desta configuracao com Alembic, apague esse arquivo uma vez antes de rodar a migracao inicial.

```bash
pip install -e .[dev]
python -m alembic upgrade head
python -m uvicorn app.principal:app --reload
```

## Execucao no PowerShell

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.principal:app --reload
```

## Testes

```bash
python -m pytest
```

No PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pytest
```

## Swagger

Depois de subir a API, abra:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/openapi.json`

## Fluxo no Telegram

- `/start` cria ou vincula o usuario
- `Nova atividade` abre um fluxo guiado com botoes
- o bot pede categoria por botao, depois titulo e um numero da atividade
- depois disso, o usuario envia PDF ou imagem do comprovante direto no chat
- `Comprovantes` lista os anexos da submissao ativa
- a remocao de comprovantes acontece por botao inline
- `Finalizar envio` conclui a submissao e consolida a estimativa

## Deploy com PostgreSQL

No Railway ou em outro ambiente de deploy, troque so a `DATABASE_URL` para a conexao real do Postgres:

```env
DATABASE_URL=postgresql+psycopg://USUARIO:SENHA@HOST:PORTA/BANCO
```

O resto pode continuar igual, ajustando o `STORAGE_DIR` para um caminho persistente do servidor.

Resumo pratico:

- local: `.env` com SQLite
- deploy: variaveis do provedor com PostgreSQL
- `.env.example`: base pronta para desenvolvimento local
- `.env.railway.example`: referencia para preencher as variaveis do Railway

## Deploy do webhook

Defina no `.env`:

```env
TELEGRAM_BOT_TOKEN=seu_token
TELEGRAM_WEBHOOK_URL=https://seu-dominio.com/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=um_token_secreto
TELEGRAM_AUTO_SET_WEBHOOK=true
```

Se preferir sincronizar manualmente depois do deploy, use:

- `POST /telegram/sync-webhook`
- `GET /telegram/webhook-info`
