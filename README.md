# DoaçãoBot - Assistente de Doações via WhatsApp

Plataforma de impacto social que conecta doadores à ONG **Mãos que Ajudam** através de uma experiência conversacional no WhatsApp, utilizando IA com LangGraph e RAG.

## Sobre o Projeto

O DoaçãoBot permite que usuários interajam via WhatsApp para:

- **Fazer doações** — receber dados bancários, PIX e orientações
- **Buscar ajuda** — ser encaminhado para assistência social
- **Ser voluntário** — conhecer oportunidades de voluntariado
- **Obter informações** — saber mais sobre a ONG e seus projetos
- **Parcerias corporativas** — conectar empresas à causa

## Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  WhatsApp   │────▶│   Z-API      │────▶│  FastAPI        │
│  (Usuário)  │◀────│  (Webhook)   │◀────│  (Backend)      │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
                                          ┌───────┴─────────┐
                                          │                 │
                                    ┌─────▼─────┐   ┌──────▼──────┐
                                    │ LangGraph │   │ PostgreSQL  │
                                    │ (Agente)  │   │ (Dados)     │
                                    └─────┬─────┘   └─────────────┘
                                          │
                                    ┌─────▼──────┐
                                    │  RAG /     │
                                    │  FAISS     │
                                    └────────────┘
```

### Fluxo de uma mensagem

1. Usuário envia mensagem no WhatsApp
2. Z-API recebe e dispara webhook `POST /api/webhook`
3. FastAPI recebe o payload, extrai telefone e mensagem
4. Busca/cria sessão de conversa no PostgreSQL
5. Agente LangGraph processa a mensagem:
   - **Classify** — GPT-4.1-mini identifica intent e sentimento
   - **Retrieve** — FAISS busca interações similares na base RAG
   - **Generate** — GPT-4.1-mini gera resposta contextualizada
6. Resposta é salva no banco e enviada via Z-API

### Intents suportados

| Intent | Descrição |
|--------|-----------|
| Quero Doar | Doação via PIX, transferência, roupas, alimentos |
| Busco Ajuda/Beneficiário | Usuário precisa de assistência |
| Voluntariado | Interesse em ser voluntário |
| Parceria Corporativa | Empresa buscando parceria |
| Informação Geral | Perguntas sobre a ONG |
| Ambíguo | Mensagem sem intenção clara |

## Stack Tecnológica

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.13+ |
| Framework Web | FastAPI |
| Motor de Conversação | LangGraph |
| LLM | OpenAI GPT-4.1-mini |
| Embeddings/RAG | OpenAI Embeddings (text-embedding-3-small) + FAISS |
| Banco de Dados | PostgreSQL (local: Docker / produção: Supabase) |
| ORM | SQLAlchemy + Alembic |
| Containerização | Docker + Docker Compose |
| Hosting | Render |
| WhatsApp | Z-API |

## Estrutura do Projeto

```
doacao-whatsapp/
├── app/
│   ├── main.py                  # FastAPI app + logging
│   ├── config.py                # Settings (pydantic-settings)
│   ├── database.py              # SQLAlchemy engine e session
│   ├── api/routes/
│   │   ├── health.py            # GET /api/health
│   │   └── webhook.py           # POST /api/webhook (Z-API)
│   ├── models/
│   │   ├── conversation.py      # Model Conversation
│   │   └── message.py           # Model Message
│   ├── schemas/
│   │   └── webhook.py           # Schemas do payload Z-API
│   ├── services/
│   │   ├── zapi_service.py      # Envio de mensagens via Z-API
│   │   └── conversation_service.py  # Gerenciamento de conversas
│   ├── agent/
│   │   ├── graph.py             # Grafo LangGraph (classify → retrieve → generate)
│   │   ├── nodes.py             # Nós: classify, retrieve, generate
│   │   ├── state.py             # ConversationState (TypedDict)
│   │   └── prompts.py           # Prompts de classificação e geração
│   └── rag/
│       ├── loader.py            # Carrega BASE_INTERACTION.json
│       └── retriever.py         # FAISS vectorstore + similarity search
├── alembic/
│   ├── env.py                   # Configuração Alembic
│   └── versions/                # Migrations
├── data/
│   └── BASE_INTERACTION.json    # Base de conhecimento RAG
├── docker-compose.yml           # App + PostgreSQL
├── Dockerfile                   # Python 3.13-slim
├── alembic.ini
├── requirements.txt
└── .env.example
```

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/)
- Conta na [OpenAI](https://platform.openai.com/) com API key
- Conta no [Z-API](https://www.z-api.io/) com instância configurada

## Como Executar

### 1. Clone o repositório

```bash
git clone https://github.com/leonardosouza/doacao-whatsapp.git
cd doacao-whatsapp
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env.development
```

Edite o `.env.development` com suas credenciais:

```env
# App
APP_NAME=DoaçãoBot
APP_ENV=development
DEBUG=True

# OpenAI
OPENAI_API_KEY=sk-sua-chave-openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_TEMPERATURE=0.3

# Z-API
ZAPI_INSTANCE_ID=seu-instance-id
ZAPI_TOKEN=seu-token
ZAPI_CLIENT_TOKEN=seu-client-token

# Database
DATABASE_URL=postgresql://doacao_user:doacao_pass@db:5432/doacao_db

# PostgreSQL (usado pelo docker-compose)
POSTGRES_USER=doacao_user
POSTGRES_PASSWORD=doacao_pass
POSTGRES_DB=doacao_db
```

> A aplicação carrega automaticamente o arquivo `.env.{APP_ENV}` conforme o valor de `APP_ENV` (default: `development`).

### 3. Inicie os containers

```bash
docker compose up --build
```

A aplicação estará disponível em `http://localhost:80`.

### 4. Execute as migrations

```bash
docker compose exec app alembic upgrade head
```

### 5. Configure o webhook no Z-API

No painel do Z-API, configure a URL de webhook para:

```
https://seu-dominio.com/api/webhook
```

> Para desenvolvimento local, utilize [ngrok](https://ngrok.com/) ou similar para expor a porta 80.

## Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/health` | Health check (verifica banco de dados e Z-API) |
| `POST` | `/api/webhook` | Recebe mensagens do Z-API |
| `GET` | `/docs` | Documentação Swagger (apenas quando `DEBUG=True`) |
| `GET` | `/redoc` | Documentação ReDoc (apenas quando `DEBUG=True`) |

## Variáveis de Ambiente

| Variável | Descrição | Obrigatória | Default |
|----------|-----------|:-----------:|---------|
| `APP_NAME` | Nome da aplicação | Sim | — |
| `APP_ENV` | Ambiente (`development`, `production`) | Não | `development` |
| `DEBUG` | Habilita Swagger e modo debug | Não | `False` |
| `OPENAI_API_KEY` | Chave da API OpenAI | Sim | — |
| `OPENAI_MODEL` | Modelo LLM utilizado | Sim | — |
| `OPENAI_EMBEDDING_MODEL` | Modelo de embeddings | Sim | — |
| `OPENAI_TEMPERATURE` | Temperatura de geração | Não | `0.3` |
| `ZAPI_INSTANCE_ID` | ID da instância Z-API | Sim | — |
| `ZAPI_TOKEN` | Token de autenticação Z-API | Sim | — |
| `ZAPI_CLIENT_TOKEN` | Client token do Z-API | Sim | — |
| `DATABASE_URL` | URL de conexão PostgreSQL | Sim | — |
| `POSTGRES_USER` | Usuário PostgreSQL (docker-compose) | Não | `doacao_user` |
| `POSTGRES_PASSWORD` | Senha PostgreSQL (docker-compose) | Não | `doacao_pass` |
| `POSTGRES_DB` | Nome do banco (docker-compose) | Não | `doacao_db` |

## Deploy em Produção

A aplicação está hospedada no [Render](https://render.com/) com banco de dados [Supabase](https://supabase.com/).

### Infraestrutura

| Serviço | Plataforma |
|---------|------------|
| Aplicação (FastAPI) | Render (Web Service) |
| Banco de Dados (PostgreSQL) | Supabase (Connection Pooler) |

### Configuração

1. Crie um Web Service no Render apontando para este repositório
2. Configure as variáveis de ambiente no painel do Render (mesmas do `.env.production`)
3. Para o `DATABASE_URL`, utilize a connection string do Supabase (pooler)
4. Configure o webhook no Z-API apontando para `https://seu-app.onrender.com/api/webhook`

### Health Check

Verifique o status da aplicação e conexão com o banco:

```bash
curl https://seu-app.onrender.com/api/health
# {"status": "ok", "database": "connected", "zapi": "connected"}
```

## Desenvolvimento Local

```bash
# Subir apenas o banco de dados
docker compose up db -d

# Instalar dependências localmente
pip install -r requirements.txt

# Rodar a aplicação
uvicorn app.main:app --reload --port 80
```

## Licença

MIT
