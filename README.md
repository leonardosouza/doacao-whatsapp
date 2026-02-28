# DoaZap - Assistente de Doações via WhatsApp

Plataforma de impacto social que conecta doadores a diversas **ONGs parceiras** através de uma experiência conversacional no WhatsApp, utilizando IA com LangGraph e RAG.

## Sobre o Projeto

O DoaZap permite que usuários interajam via WhatsApp para:

- **Fazer doações** — receber dados bancários, PIX e orientações
- **Buscar ajuda** — ser encaminhado para assistência social
- **Ser voluntário** — conhecer oportunidades de voluntariado
- **Obter informações** — saber mais sobre as ONGs parceiras e seus projetos
- **Parcerias corporativas** — conectar empresas à causa

O atendimento é personalizado: na primeira mensagem, o bot **se apresenta** (missão e serviços do DoaZap) e, em seguida, coleta o nome do usuário. Uma vez registrado, o nome não é solicitado novamente.

## Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  WhatsApp   │────▶│   Z-API      │────▶│  FastAPI        │
│  (Usuário)  │◀────│  (Webhook)   │◀────│  (Backend)      │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
                                          ┌───────┴─────────┐
                                          │                 │
                                    ┌─────▼─────┐    ┌──────▼──────┐
                                    │ LangGraph │    │ PostgreSQL  │
                                    │ (Agente)  │    │ (Dados)     │
                                    └─────┬─────┘    └─────────────┘
                                          │
                                    ┌─────▼──────┐
                                    │  RAG /     │
                                    │  FAISS     │
                                    └────────────┘
```

### Fluxo de uma mensagem

1. Usuário envia mensagem no WhatsApp
2. Z-API recebe e dispara webhook `POST /api/webhook`
3. FastAPI recebe o payload e aplica filtros sequenciais:
   - Mensagens `fromMe` ou de grupo → ignoradas silenciosamente
   - **Mídia** (áudio, vídeo, imagem, documento, sticker) → envia aviso ao usuário e encerra
   - **Rate limit** excedido (> 12 msgs/min do mesmo número) → ignorado silenciosamente
   - Sem texto → ignorado silenciosamente
   - **Bot detectado** por auto-identificação na mensagem → ignorado silenciosamente
   - `messageId` já processado → descartado (deduplicação de webhook duplicado pelo Z-API)
4. Busca/cria sessão de conversa no PostgreSQL
5. Salva a mensagem inbound com o `messageId` do Z-API (garante idempotência)
6. Recupera histórico das últimas mensagens da conversa (memória conversacional)
7. Agente LangGraph processa a mensagem:
   - **Profile** — verifica/coleta o nome do usuário nas primeiras interações:
     - **1ª mensagem** (`greeting`): apresenta o DoaZap, reconhece brevemente a intenção e pede o nome
     - **2ª mensagem** (`collecting_name`): pede o nome novamente se não foi fornecido
     - Nome extraído via LLM (`EXTRACT_NAME_PROMPT`) e persistido no banco
   - **Classify** — GPT-4.1-mini identifica intent e sentimento (com guard-rails)
   - **Retrieve** — FAISS busca interações similares na base RAG
   - **Enrich** — Consulta ONGs parceiras no banco conforme o intent
   - **Generate** — GPT-4.1-mini gera resposta contextualizada com dados reais das ONGs
8. Resposta é salva no banco e enviada via Z-API

### Intents suportados

| Intent | Descrição |
|--------|-----------|
| Quero Doar | Doação via PIX, transferência, roupas, alimentos |
| Busco Ajuda/Beneficiário | Usuário precisa de assistência |
| Voluntariado | Interesse em ser voluntário |
| Parceria Corporativa | Empresa buscando parceria |
| Informação Geral | Perguntas sobre as ONGs parceiras |
| Ambíguo | Mensagem sem intenção clara relacionada à plataforma |
| Fora do Escopo | Mensagem não relacionada a doações, ONGs ou assistência social |

### Guard-rails e segurança

O sistema possui três camadas de proteção independentes:

**Camada 1 — Rate limiting (webhook):** Máximo de 12 mensagens por minuto por número de telefone, usando janela deslizante em memória. Excedido o limite, a mensagem é descartada silenciosamente (sem resposta), interrompendo loops de bots automatizados.

**Camada 2 — Detecção de bot por auto-identificação (webhook):** Mensagens que contêm frases típicas de assistentes virtuais ("sou a analista virtual", "sou um assistente virtual", "atendente virtual da…") são descartadas silenciosamente antes de qualquer processamento pelo agente.

**Camada 3 — Limite de tentativas de coleta de nome (agente):** O estágio de coleta do nome do usuário tem no máximo 3 tentativas. Após esse limite, o bot prossegue o atendimento normalmente sem nome, evitando o loop infinito caso um bot externo não consiga fornecer uma resposta válida.

**Guard-rails do agente (LLM):** Mensagens classificadas como "Fora do Escopo" recebem uma resposta gentil de redirecionamento, sem acesso ao banco de ONGs.

Padrões bloqueados automaticamente:

- Perguntas de cultura pop, esportes, ciência geral, política
- Tentativas de **prompt injection** ("ignore suas instruções…")
- Tentativas de **jailbreak** ("DAN", "modo sem restrições"…)
- Impersonação de outro bot ou serviço externo (cobranças, boletos)
- Solicitação do prompt de sistema ou de outra identidade

### Tratamento de mídia

Mensagens de áudio, vídeo, imagem, documento ou sticker são identificadas pelo tipo do payload Z-API e recebem uma resposta automática informando que o bot processa apenas texto. O agente não é acionado para esse tipo de conteúdo.

### Resiliência do webhook

O Z-API pode reenviar o mesmo webhook quando o servidor demora a responder. Para evitar respostas duplicadas, cada mensagem inbound é gravada com o `messageId` do Z-API (campo único no banco). Webhooks com `messageId` já registrado são descartados imediatamente, antes de qualquer chamada ao agente.

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
| Testes | pytest + pytest-asyncio + pytest-cov |
| Hosting | Render |
| WhatsApp | Z-API |
| Observabilidade | New Relic APM |

## Estrutura do Projeto

```
doacao-whatsapp/
├── app/
│   ├── main.py                  # FastAPI app + logging
│   ├── config.py                # Settings (pydantic-settings)
│   ├── database.py              # SQLAlchemy engine e session
│   ├── security.py              # API Key auth (protege rotas de escrita)
│   ├── api/routes/
│   │   ├── health.py            # GET e POST /api/health
│   │   ├── webhook.py           # POST /api/webhook (Z-API)
│   │   └── ong.py               # CRUD /api/ongs (ONGs parceiras)
│   ├── models/
│   │   ├── conversation.py      # Model Conversation
│   │   ├── message.py           # Model Message
│   │   └── ong.py               # Model Ong (ONGs parceiras)
│   ├── schemas/
│   │   ├── webhook.py           # Schemas do payload Z-API (text, audio, video, image, document, sticker)
│   │   └── ong.py               # Schemas de ONG (create/update/response)
│   ├── services/
│   │   ├── zapi_service.py      # Envio de mensagens via Z-API
│   │   ├── conversation_service.py  # Gerenciamento de conversas
│   │   └── ong_service.py       # CRUD de ONGs parceiras
│   ├── agent/
│   │   ├── graph.py             # Grafo LangGraph (profile → classify → retrieve → enrich → generate)
│   │   ├── nodes.py             # Nós: profile, classify, retrieve, enrich, generate + guard-rails
│   │   ├── state.py             # ConversationState (TypedDict)
│   │   └── prompts.py           # Prompts de perfil, classificação e geração
│   └── rag/
│       ├── loader.py            # Carrega BASE_INTERACTION.json
│       └── retriever.py         # FAISS vectorstore + similarity search
├── scripts/
│   └── seed_ongs.py             # Seed de ONGs a partir de ONGS.json
├── alembic/
│   ├── env.py                   # Configuração Alembic
│   └── versions/                # Migrations (001 → 011)
├── data/
│   ├── BASE_INTERACTION.json    # Base de conhecimento RAG (65 interações)
│   ├── ONGS.json                # Dados originais (19 ONGs)
│   ├── ONGS_v2.csv              # Dados ampliados (52 ONGs)
│   └── seed_ongs_v2.sql         # Seed aplicado em 2026-02-28
├── tests/                         # 144 testes automatizados (99% cobertura)
├── docker-compose.yml           # App + PostgreSQL
├── Dockerfile                   # Python 3.13-slim
├── alembic.ini
├── pyproject.toml               # Configuração pytest
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

## Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/health` | Health check (verifica banco de dados e Z-API) |
| `POST` | `/api/health` | Health check via POST (para monitor sintético New Relic) |
| `POST` | `/api/webhook` | Recebe mensagens do Z-API |
| `GET` | `/api/ongs` | Lista todas as ONGs parceiras |
| `GET` | `/api/ongs/{id}` | Retorna uma ONG pelo ID |
| `POST` | `/api/ongs` | Cadastra nova ONG parceira 🔒 |
| `PUT` | `/api/ongs/{id}` | Atualiza dados de uma ONG 🔒 |
| `DELETE` | `/api/ongs/{id}` | Remove uma ONG 🔒 |
| `GET` | `/docs` | Documentação Swagger (apenas quando `DEBUG=True`) |
| `GET` | `/redoc` | Documentação ReDoc (apenas quando `DEBUG=True`) |

> 🔒 Rotas protegidas por API Key. Envie o header `X-API-Key` com a chave configurada em `API_KEY`.

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

## Deploy em Produção

A aplicação está hospedada no [Render](https://render.com/) com banco de dados [Supabase](https://supabase.com/).

### Infraestrutura

| Serviço | Plataforma |
|---------|------------|
| Aplicação (FastAPI) | Render (Web Service) |
| Banco de Dados (PostgreSQL) | Supabase (Connection Pooler) |
| Monitoramento / APM | New Relic |

### Configuração

1. Crie um Web Service no Render apontando para este repositório
2. Configure as variáveis de ambiente no painel do Render (mesmas do `.env.production`)
3. Para o `DATABASE_URL`, utilize a connection string do Supabase (pooler)
4. Configure as variáveis `NEW_RELIC_LICENSE_KEY` e `NEW_RELIC_APP_NAME` no Render
5. Configure o webhook no Z-API apontando para `https://doacao-whatsapp.onrender.com/api/webhook`

O agente New Relic é iniciado automaticamente via `newrelic-admin run-program` (definido no `Dockerfile`), sem necessidade de arquivo de configuração no repositório.

### Health Check

Verifique o status da aplicação e conexão com o banco:

```bash
curl https://doacao-whatsapp.onrender.com/api/health
# {"status": "ok", "database": "connected", "zapi": "connected"}
```

### Monitoramento (New Relic APM)

Acesse as métricas de performance, erros e throughput em:

| Ambiente | URL |
|----------|-----|
| Produção (`DoaZap`) | [one.newrelic.com → APM & Services → DoaZap](https://one.newrelic.com/apm) |
| Desenvolvimento (`DoaZap (Dev)`) | [one.newrelic.com → APM & Services → DoaZap (Dev)](https://one.newrelic.com/apm) |

> O ambiente de desenvolvimento só aparece no New Relic enquanto a aplicação local estiver rodando com as variáveis `NEW_RELIC_*` configuradas no `.env.development`.

### Monitor Sintético (New Relic Synthetics)

O endpoint `POST /api/health` está disponível para uso com o [New Relic Synthetics](https://one.newrelic.com/synthetics):

```
https://doacao-whatsapp.onrender.com/api/health
Método: POST
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

## Testes

O projeto possui **152 testes automatizados** com **99% de cobertura**, utilizando SQLite in-memory para isolamento completo (sem dependências externas).

### Executar os testes

```bash
# Instalar dependências (inclui pytest, pytest-asyncio, pytest-cov)
pip install -r requirements.txt

# Rodar todos os testes
pytest

# Com relatório de cobertura
pytest --cov=app --cov-report=term-missing

# Gerar relatório HTML de cobertura
pytest --cov=app --cov-report=html
# Abrir htmlcov/index.html
```

### Estrutura dos testes

```
tests/
├── conftest.py                        # Fixtures globais (DB, client, dados)
├── test_schemas/
│   ├── test_webhook_schemas.py        # Validação dos payloads Z-API
│   └── test_ong_schemas.py            # Validação dos schemas de ONG
├── test_security/
│   └── test_require_api_key.py        # Autenticação por API Key
├── test_services/
│   ├── test_conversation_service.py   # Gerenciamento de conversas
│   ├── test_ong_service.py            # CRUD de ONGs
│   └── test_zapi_service.py           # Integração Z-API (mock)
├── test_api/
│   ├── test_health.py                 # Health check endpoint
│   ├── test_ong_routes.py             # Rotas CRUD de ONGs
│   └── test_webhook.py                # Webhook do WhatsApp
├── test_agent/
│   ├── test_nodes.py                  # Nós do LangGraph (profile, classify, retrieve, enrich, generate)
│   └── test_graph.py                  # Grafo compilado e fluxo end-to-end
└── test_rag/
    ├── test_loader.py                 # Carregamento da base de conhecimento
    └── test_retriever.py              # Vectorstore FAISS e busca por similaridade
```

### Cobertura por módulo

| Módulo | Cobertura |
|--------|:---------:|
| agent (graph, nodes, prompts, state) | 100% |
| api/routes (health, webhook, ong) | 100% |
| schemas (webhook, ong) | 100% |
| security | 100% |
| services (conversation, ong, zapi) | 100% |
| rag (loader, retriever) | 100% |
| config, main | 100% |
| models (conversation, message, ong) | 100% |

## Testes de Carga

Scripts e relatórios de stress test mantidos no repositório [doazap-stress-test](https://github.com/leonardosouza/doazap-stress-test) (Locust).

| Cenário | Markdown | HTML interativo |
|---------|----------|-----------------|
| Consolidado (análise geral + ponto de ruptura) | [report_consolidado.md](https://github.com/leonardosouza/doazap-stress-test/blob/main/reports/markdown/report_consolidado.md) | — |
| 10 usuários simultâneos | [report_10u.md](https://github.com/leonardosouza/doazap-stress-test/blob/main/reports/markdown/report_10u.md) | [report_10u.html](https://leonardosouza.github.io/doazap-stress-test/reports/html/report_10u.html) |
| 20 usuários simultâneos | [report_20u.md](https://github.com/leonardosouza/doazap-stress-test/blob/main/reports/markdown/report_20u.md) | [report_20u.html](https://leonardosouza.github.io/doazap-stress-test/reports/html/report_20u.html) |
| 30 usuários simultâneos | [report_30u.md](https://github.com/leonardosouza/doazap-stress-test/blob/main/reports/markdown/report_30u.md) | [report_30u.html](https://leonardosouza.github.io/doazap-stress-test/reports/html/report_30u.html) |
| 50 usuários simultâneos | [report_50u.md](https://github.com/leonardosouza/doazap-stress-test/blob/main/reports/markdown/report_50u.md) | [report_50u.html](https://leonardosouza.github.io/doazap-stress-test/reports/html/report_50u.html) |
| 100 usuários simultâneos | [report_100u.md](https://github.com/leonardosouza/doazap-stress-test/blob/main/reports/markdown/report_100u.md) | [report_100u.html](https://leonardosouza.github.io/doazap-stress-test/reports/html/report_100u.html) |

> O ponto de ruptura identificado é entre **20 e 30 usuários simultâneos** no plano Free Tier do Render.

## Changelog

Todas as versões e mudanças estão documentadas em [CHANGELOG.md](CHANGELOG.md).

## Equipe

Projeto desenvolvido pelo **Grupo 02** do MBA em Engenharia de Software — [Faculdade Impacta](https://www.impacta.edu.br/).

| Nome | E-mail |
|------|--------|
| Diego de Jesus | diego.jesus@aluno.impacta.edu.br |
| Janailson Rocha de Sousa | janailson.sousa@aluno.impacta.edu.br |
| Jeferson Borges | jeferson.borges@aluno.impacta.edu.br |
| João Victor Ribeiro Borges | joao.rborges@aluno.impacta.edu.br |
| Kaio Candido de Oliveira | kaio.candido@aluno.impacta.edu.br |
| Leonardo Souza | leonardo.aparecido@aluno.impacta.edu.br |
| Lucas Cassidori | lucas.cassidori@aluno.impacta.edu.br |
| Ricardo Barreto Gusi | ricardo.gusi@aluno.impacta.edu.br |
| Ronildo Mendes Viana | ronildo.viana@aluno.impacta.edu.br |
| Vinicius Alcarde Goia | vinicius.goia@aluno.impacta.edu.br |

## Licença

MIT
