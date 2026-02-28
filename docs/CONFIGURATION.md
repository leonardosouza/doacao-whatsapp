# Configuração e Execução

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
APP_NAME=DoaZap
APP_ENV=development
DEBUG=True
API_KEY=sua-api-key-secreta

# OpenAI
OPENAI_API_KEY=sk-sua-chave-openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_TEMPERATURE=0.3

# Z-API
ZAPI_INSTANCE_ID=seu-instance-id
ZAPI_TOKEN=seu-token
ZAPI_CLIENT_TOKEN=seu-client-token

# Conversation
CONVERSATION_HISTORY_LIMIT=10

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

## Desenvolvimento Local

```bash
# Subir apenas o banco de dados
docker compose up db -d

# Instalar dependências localmente
pip install -r requirements.txt

# Rodar a aplicação
uvicorn app.main:app --reload --port 80
```

## Variáveis de Ambiente

| Variável | Descrição | Obrigatória | Default |
|----------|-----------|:-----------:|---------|
| `APP_NAME` | Nome da aplicação | Sim | — |
| `APP_ENV` | Ambiente (`development`, `production`) | Não | `development` |
| `DEBUG` | Habilita Swagger e modo debug | Não | `False` |
| `API_KEY` | Chave para proteger rotas de escrita (ONGs) | Sim | — |
| `OPENAI_API_KEY` | Chave da API OpenAI | Sim | — |
| `OPENAI_MODEL` | Modelo LLM utilizado | Sim | — |
| `OPENAI_EMBEDDING_MODEL` | Modelo de embeddings | Sim | — |
| `OPENAI_TEMPERATURE` | Temperatura de geração | Não | `0.3` |
| `ZAPI_INSTANCE_ID` | ID da instância Z-API | Sim | — |
| `ZAPI_TOKEN` | Token de autenticação Z-API | Sim | — |
| `ZAPI_CLIENT_TOKEN` | Client token do Z-API | Sim | — |
| `DATABASE_URL` | URL de conexão PostgreSQL | Sim | — |
| `CONVERSATION_HISTORY_LIMIT` | Número máximo de mensagens no histórico do agente | Não | `10` |
| `POSTGRES_USER` | Usuário PostgreSQL (docker-compose) | Não | `doacao_user` |
| `POSTGRES_PASSWORD` | Senha PostgreSQL (docker-compose) | Não | `doacao_pass` |
| `POSTGRES_DB` | Nome do banco (docker-compose) | Não | `doacao_db` |
| `NEW_RELIC_LICENSE_KEY` | Chave de licença do New Relic (Ingest - License) | Sim | — |
| `NEW_RELIC_APP_NAME` | Nome da aplicação no New Relic | Não | `DoaZap` |
| `NEW_RELIC_LOG` | Destino dos logs do agente New Relic | Não | `stdout` |
| `NEW_RELIC_LOG_LEVEL` | Nível de log do agente New Relic | Não | `info` |
| `NEW_RELIC_DISTRIBUTED_TRACING_ENABLED` | Habilita rastreamento distribuído | Não | `true` |

## Segurança do Banco de Dados

### Row Level Security (RLS) no Supabase

Todas as tabelas do schema `public` têm **Row Level Security habilitado** para bloquear acesso direto via API REST do Supabase (PostgREST), que usa o role `anon` por padrão.

| Tabela | RLS | Política `anon` |
|--------|:---:|-----------------|
| `ongs` | ✅ | SELECT permitido (dado público, consistente com GET /api/ongs) |
| `conversations` | ✅ | Nenhuma — bloqueado completamente |
| `messages` | ✅ | Nenhuma — bloqueado completamente |
| `alembic_version` | ✅ | Nenhuma — bloqueado completamente |

O app FastAPI conecta como `postgres` (superusuário) e **não é afetado** pelo RLS — superusuários contornam RLS por padrão no PostgreSQL. O Alembic também opera como superusuário e continua executando migrations normalmente.
