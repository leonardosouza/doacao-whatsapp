# DoaZap — Assistente de Doações via WhatsApp

Plataforma de impacto social que conecta doadores a **275 ONGs parceiras** através de uma experiência conversacional no WhatsApp, utilizando IA com LangGraph e RAG.

## Sobre o Projeto

O DoaZap permite que usuários interajam via WhatsApp para:

- **Fazer doações** — receber dados bancários, PIX e orientações
- **Buscar ajuda** — ser encaminhado para assistência social
- **Ser voluntário** — conhecer oportunidades de voluntariado
- **Obter informações** — saber mais sobre as ONGs parceiras e seus projetos
- **Parcerias corporativas** — conectar empresas à causa

O atendimento é personalizado: na primeira mensagem, o bot **se apresenta** (missão e serviços do DoaZap) e, em seguida, coleta o nome do usuário. Uma vez registrado, o nome não é solicitado novamente.

---

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

---

## Estrutura do Projeto

```
doacao-whatsapp/
├── app/
│   ├── main.py                  # FastAPI app + logging em horário SP (UTC-3)
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
│   ├── seed_ongs.py             # Seed de ONGs a partir de ONGS.json
│   ├── psql-production.sh       # psql com timezone São Paulo (UTC-3)
│   └── generate_graph.py        # Exporta diagrama PNG do grafo LangGraph
├── alembic/
│   ├── env.py                   # Configuração Alembic
│   └── versions/                # Migrations (001 → 014)
├── data/
│   ├── BASE_INTERACTION.json    # Base de conhecimento RAG (65 interações)
│   ├── seed_ongs_v2.sql         # Seed de 52 ONGs (2026-02-28)
│   └── seed_ongs_v3.sql         # Seed de 223 ONGs da ABONG (2026-02-28)
├── tests/                       # 192 testes automatizados (99% cobertura)
├── docs/
│   ├── agent_graph.png          # Diagrama visual do grafo LangGraph
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── CONFIGURATION.md
│   ├── DEPLOY.md
│   ├── TESTING.md
│   ├── OBSERVABILITY.md
│   └── SECURITY.md
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## Arquitetura

### Visão Geral

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

### Fluxo de uma Mensagem

1. Usuário envia mensagem no WhatsApp
2. Z-API recebe e dispara webhook `POST /api/webhook`
3. FastAPI recebe o payload e aplica filtros sequenciais:
   - **`instanceId` inválido** → rejeitado silenciosamente
   - Mensagens `fromMe` ou de grupo → ignoradas silenciosamente
   - **Mídia** (áudio, vídeo, imagem, documento, sticker) → envia aviso ao usuário e encerra
   - **Rate limit** excedido (≥ 5 msgs/60s do mesmo número, via banco de dados) → ignorado silenciosamente
   - Sem texto → ignorado silenciosamente
   - **Bot detectado** por auto-identificação na mensagem → ignorado silenciosamente
   - `messageId` já processado → descartado (deduplicação de webhook duplicado pelo Z-API)
   - **Circuit breaker OOS** ativado (3 de 6 respostas "Fora do Escopo" em 2 min) → ignorado silenciosamente
4. Busca/cria sessão de conversa no PostgreSQL
5. Salva a mensagem inbound com o `messageId` do Z-API (garante idempotência)
6. Recupera histórico das últimas mensagens da conversa (memória conversacional)
7. Agente LangGraph processa a mensagem:
   - **Profile** — verifica/coleta o nome do usuário nas primeiras interações
   - **Classify** — GPT-4.1-mini identifica intent e sentimento
   - **Retrieve** — FAISS busca interações similares na base RAG
   - **Enrich** — Consulta ONGs parceiras no banco conforme o intent
   - **Generate** — GPT-4.1-mini gera resposta contextualizada com dados reais das ONGs
8. Resposta é salva no banco e enviada via Z-API

### Grafo do Agente LangGraph

O grafo possui dois caminhos a partir do nó `profile`:

- **Fluxo de coleta de nome** (1ª e 2ª mensagem): `profile` → `profile_response` → `END`
- **Fluxo principal** (usuário já identificado): `profile` → `classify` → `retrieve` → `enrich` → `generate` → `END`

### Intents Suportados

| Intent | Descrição |
|--------|-----------|
| Quero Doar | Doação via PIX, transferência, roupas, alimentos |
| Busco Ajuda/Beneficiário | Usuário precisa de assistência |
| Voluntariado | Interesse em ser voluntário |
| Parceria Corporativa | Empresa buscando parceria |
| Informação Geral | Perguntas sobre as ONGs parceiras e seus projetos |
| Ambíguo | Mensagem sem intenção clara relacionada à plataforma |
| Fora do Escopo | Mensagem não relacionada a doações, ONGs ou assistência social |

---

## API Reference

### Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/health` | Health check (verifica banco de dados e Z-API) |
| `POST` | `/api/health` | Health check via POST (para monitor sintético New Relic) |
| `POST` | `/api/webhook` | Recebe mensagens do Z-API |
| `GET` | `/api/ongs` | Lista ONGs (filtros: `category`, `state`, `city`, `q`, `name`) |
| `GET` | `/api/ongs/{id}` | Retorna uma ONG pelo ID |
| `POST` | `/api/ongs` | Cadastra nova ONG parceira 🔒 |
| `PUT` | `/api/ongs/{id}` | Atualiza dados de uma ONG 🔒 |
| `DELETE` | `/api/ongs/{id}` | Remove uma ONG 🔒 |
| `GET` | `/docs` | Documentação Swagger (apenas quando `DEBUG=True`) |
| `GET` | `/redoc` | Documentação ReDoc (apenas quando `DEBUG=True`) |

> 🔒 Rotas protegidas por API Key. Envie o header `X-API-Key` com a chave configurada em `API_KEY`.

### GET /api/ongs — Parâmetros de Busca

| Parâmetro | Tipo | Descrição | Exemplo |
|-----------|------|-----------|---------|
| `category` | string | Filtro por categoria (ILIKE) | `?category=Saúde` |
| `state` | string | Filtro por UF — exato, 2 letras | `?state=SP` |
| `city` | string | Filtro por cidade (ILIKE) | `?city=São Paulo` |
| `q` | string | Busca livre em **nome** e **subcategoria** (ILIKE) | `?q=lgbt`, `?q=meio+ambiente` |
| `name` | string | Filtro por nome parcial (ILIKE) | `?name=byler` |
| `active_only` | bool | Apenas ONGs ativas (padrão: `true`) | `?active_only=false` |
| `skip` | int | Offset para paginação (padrão: `0`) | `?skip=50` |
| `limit` | int | Máximo de resultados — 1 a 100 (padrão: `50`) | `?limit=20` |

Os parâmetros são combináveis: `?q=lgbt&state=SP` retorna ONGs LGBTQIA+ em SP.

### Autenticação

Rotas de escrita (POST, PUT, DELETE em `/api/ongs`) exigem o header:

```
X-API-Key: sua-api-key-secreta
```

### Health Check

```bash
curl https://doacao-whatsapp.onrender.com/api/health
# {"status": "ok", "database": "connected", "zapi": "connected"}
```

---

## Configuração e Execução

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/)
- Conta na [OpenAI](https://platform.openai.com/) com API key
- Conta no [Z-API](https://www.z-api.io/) com instância configurada

### Como Executar

#### 1. Clone o repositório

```bash
git clone https://github.com/leonardosouza/doacao-whatsapp.git
cd doacao-whatsapp
```

#### 2. Configure as variáveis de ambiente

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

#### 3. Inicie os containers

```bash
docker compose up --build
```

A aplicação estará disponível em `http://localhost:80`.

#### 4. Execute as migrations

```bash
docker compose exec app alembic upgrade head
```

#### 5. Configure o webhook no Z-API

No painel do Z-API, configure a URL de webhook para:

```
https://seu-dominio.com/api/webhook
```

> Para desenvolvimento local, utilize [ngrok](https://ngrok.com/) ou similar para expor a porta 80.

### Desenvolvimento Local

```bash
# Subir apenas o banco de dados
docker compose up db -d

# Instalar dependências localmente
pip install -r requirements.txt

# Rodar a aplicação
uvicorn app.main:app --reload --port 80
```

### Variáveis de Ambiente

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

---

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

O agente New Relic é iniciado automaticamente via `newrelic-admin run-program` (definido no `Dockerfile`).

### Monitoramento (New Relic APM)

| Ambiente | URL |
|----------|-----|
| Produção (`DoaZap`) | [one.newrelic.com → APM & Services → DoaZap](https://one.newrelic.com/apm) |
| Desenvolvimento (`DoaZap (Dev)`) | [one.newrelic.com → APM & Services → DoaZap (Dev)](https://one.newrelic.com/apm) |

### Monitor Sintético (New Relic Synthetics)

O endpoint `POST /api/health` está disponível para uso com o New Relic Synthetics:

```
https://doacao-whatsapp.onrender.com/api/health
Método: POST
```

### Deploy Forçado via API

```bash
curl -s -X POST "https://api.render.com/v1/services/{SERVICE_ID}/deploys" \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"clearCache": "do_not_clear"}'
```

---

## Testes

O projeto possui **192 testes automatizados** com **99% de cobertura**, utilizando SQLite in-memory para isolamento completo.

### Executar os Testes

```bash
# Rodar todos os testes
pytest

# Com relatório de cobertura
pytest --cov=app --cov-report=term-missing

# Gerar relatório HTML de cobertura
pytest --cov=app --cov-report=html
```

### Estrutura dos Testes

```
tests/
├── conftest.py
├── test_schemas/
│   ├── test_webhook_schemas.py
│   └── test_ong_schemas.py
├── test_security/
│   └── test_require_api_key.py
├── test_services/
│   ├── test_conversation_service.py
│   ├── test_ong_service.py
│   └── test_zapi_service.py
├── test_api/
│   ├── test_health.py
│   ├── test_ong_routes.py
│   └── test_webhook.py
├── test_agent/
│   ├── test_nodes.py
│   └── test_graph.py
└── test_rag/
    ├── test_loader.py
    └── test_retriever.py
```

### Cobertura por Módulo

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

### Testes de Carga

Scripts e relatórios de stress test mantidos no repositório [doazap-stress-test](https://github.com/leonardosouza/doazap-stress-test) (Locust).

| Cenário | Relatório |
|---------|-----------|
| 10 usuários simultâneos | [report_10u.html](https://leonardosouza.github.io/doazap-stress-test/reports/html/report_10u.html) |
| 20 usuários simultâneos | [report_20u.html](https://leonardosouza.github.io/doazap-stress-test/reports/html/report_20u.html) |
| 30 usuários simultâneos | [report_30u.html](https://leonardosouza.github.io/doazap-stress-test/reports/html/report_30u.html) |
| 50 usuários simultâneos | [report_50u.html](https://leonardosouza.github.io/doazap-stress-test/reports/html/report_50u.html) |
| 100 usuários simultâneos | [report_100u.html](https://leonardosouza.github.io/doazap-stress-test/reports/html/report_100u.html) |

> O ponto de ruptura identificado é entre **20 e 30 usuários simultâneos** no plano Free Tier do Render.

---

## Segurança

### Proteção do Webhook (5 camadas sequenciais)

Toda mensagem recebida em `POST /api/webhook` passa pelos seguintes filtros em ordem:

| Camada | Mecanismo | Ação |
|--------|-----------|------|
| 0 | Validação de `instanceId` | Rejeita payloads de instâncias Z-API desconhecidas |
| 1 | Rate limiting por número (banco de dados) | Silencia após ≥ 5 msgs em 60s; sobrevive a reinicializações |
| 2 | Detecção de bot por auto-identificação | Descarta mensagens com assinaturas de CRM/assistentes virtuais |
| 3 | Circuit breaker OOS proporcional | Silencia após ≥ 3 de 6 respostas "Fora do Escopo" em 2 minutos |
| 4 | Limite de tentativas de coleta de nome | Máximo 3 tentativas; prossegue sem nome para evitar loop |

#### Camada 0 — Validação de Origem (`instanceId`)

```python
if payload.instanceId != settings.ZAPI_INSTANCE_ID:
    return {"status": "ignored", "reason": "unknown_instance"}
```

#### Camada 1 — Rate Limiting Persistente

Implementado via contagem direta na tabela `messages`. Por usar o banco de dados, o limite persiste entre deploys e reinicializações. Limite: **5 mensagens / 60 segundos** por número de telefone.

#### Camada 2 — Detecção de Bot

Padrões detectados no texto da mensagem (case-insensitive):

**Fase 1** — Assistentes virtuais genéricos:
- `sou a analista virtual`, `sou um assistente virtual`, `sou um atendente virtual`
- `analista virtual da`, `atendente virtual da`
- `posso te ajudar com diversos assuntos`
- `informe o seu cpf ou cnpj`

**Fase 2** — CRMs, NPS e bots de cobrança:
- `vou verificar se há alguma mensagem`, `desculpe, não entendi isso`
- `qual é o seu nível de satisfação`, `link de pagamento gerado`
- `queremos saber sua opinião`, `número de protocolo`, `já encontrei seu cadastro`

**Fase 3** — Concessionárias e fraudes (identificados em análise forense de produção):
- `sou a sani` (bot Sabesp)
- `2ª via de faturas` (padrão de concessionária)
- `é sua vez!` (fraude/spam promocional)
- `não vamos seguir nesse momento com` (rejeição de CRM)
- `esse cpf não é válido` / `esse cpf ou cnpj que você está` (loop de validação)

#### Camada 3 — Circuit Breaker OOS (Proporcional)

Detecta quando **ao menos 3 das últimas 6 respostas `outbound`** foram classificadas como `"Fora do Escopo"` dentro de 2 minutos. A lógica proporcional corrige um bypass onde bots intercalavam respostas `Ambíguo` para quebrar a contagem consecutiva.

#### Guard-Rails do Agente LLM

Mensagens classificadas como `"Fora do Escopo"` não acessam o banco de ONGs e recebem uma resposta gentil de redirecionamento. Padrões bloqueados:
- Perguntas de cultura pop, esportes, ciência geral, política
- Tentativas de **prompt injection** e **jailbreak**
- Impersonação de outro serviço (boletos, cobranças)
- Solicitação do prompt de sistema ou mudança de identidade

### Proteção de Dados (LGPD)

#### Mascaramento de PII nos Logs

Números de telefone são mascarados em todos os eventos de log — apenas os 4 últimos dígitos são exibidos. Conteúdo de mensagens é truncado a 30 caracteres.

```
[INFO] Mensagem recebida de ****0000: Quero fazer uma doa…
```

#### Dados Armazenados

| Dado | Armazenamento | Justificativa |
|------|---------------|---------------|
| Número de telefone | Banco de dados (criptografado em repouso pelo Supabase) | Necessário para gerenciar sessões de conversa |
| Nome do usuário | Banco de dados | Coletado com consentimento para personalizar atendimento |
| Conteúdo das mensagens | Banco de dados | Necessário para histórico conversacional |
| Intents / sentimentos | Banco de dados | Análise agregada de uso (sem identificação individual) |

### Proteção da API

- **Autenticação de escrita**: rotas `POST`, `PUT`, `DELETE` em `/api/ongs` exigem header `X-API-Key`
- **CORS restrito**: `allow_origins` limitado a `doacao-whatsapp.onrender.com` e `doazap-dashboard.onrender.com`
- **Swagger desabilitado em produção**: rotas `/docs` e `/redoc` retornam `HTTP 404` quando `DEBUG=False`
- **Escape de metacaracteres LIKE**: filtros de busca em `GET /api/ongs` escapam `%`, `_` e `\`

### Segurança do Banco de Dados

#### Row Level Security (RLS) no Supabase

| Tabela | Acesso `anon` |
|--------|---------------|
| `ongs` | SELECT permitido (dado público) |
| `conversations` | Bloqueado completamente |
| `messages` | Bloqueado completamente |
| `alembic_version` | Bloqueado completamente |

O FastAPI conecta como superusuário `postgres`, que contorna RLS por design do PostgreSQL.

### Proteção de Credenciais

- Todas as credenciais são injetadas via variáveis de ambiente — nenhum secret é hardcoded
- `.env.production` está no `.gitignore` e nunca foi commitado ao repositório
- Token Z-API é sanitizado em logs via `_safe_err()` antes de qualquer chamada a `logger.*`
- Todas as requisições HTTP para a Z-API têm timeout de **10 segundos** (`_ZAPI_TIMEOUT`)

---

## Observabilidade e Troubleshooting

O banco armazena timestamps em **UTC**. Para correlação de eventos em horário de São Paulo (UTC-3), o projeto oferece três ferramentas:

### Logs do Render

Formatados em horário de São Paulo via `_SPFormatter` em `app/main.py`:

```
2026-02-28 14:46:19,475 [INFO] app.api.routes.webhook: Mensagem processada
# (horário SP — armazenado como 17:46:19 UTC no banco)
```

### psql com Timezone SP

```bash
# Conectar ao banco
./scripts/psql-production.sh

# Executar query direta
./scripts/psql-production.sh -c "SELECT * FROM v_messages_sp LIMIT 10;"
```

### Views Diagnósticas no Banco

| View | Colunas principais |
|------|--------------------|
| `v_messages_sp` | `phone_number`, `direction`, `content`, `intent`, `created_at_sp` |
| `v_conversations_sp` | `phone_number`, `status`, `user_name`, `started_at_sp`, `last_message_at_sp` |

> Acesso restrito ao superusuário `postgres`. Nenhum GRANT concedido a `anon` ou `authenticated`.

---

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

---

## Changelog

### [1.5.10] - 2026-02-28

**Security**
- Camada 2 — Fase 3 de assinaturas de bot: 6 novas assinaturas identificadas em análise forense (bot Sabesp, fraude/spam, rejeição de CRM, loops de CPF por bot)
- Camada 3 — Circuit breaker proporcional: lógica alterada de "3 OOS consecutivos em 1 min" para "3 de 6 outbound OOS em 2 min", corrigindo bypass por intercalação de respostas `Ambíguo`

### [1.5.9] - 2026-02-28

**Security**
- Mascaramento de PII nos logs (LGPD): telefones como `****XXXX`, mensagens truncadas a 30 chars
- Sanitização de erros Z-API: token substituído por `***` em stack traces
- Timeout consistente nas requisições HTTP (`_ZAPI_TIMEOUT = 10s`)
- Validação de origem do webhook (`instanceId`) — Camada 0
- Escape de metacaracteres LIKE nos filtros de ONGs
- CORS restrito aos domínios Render da plataforma

### [1.5.8] - 2026-02-28

**Added**
- Logs do Render em horário de São Paulo via `_SPFormatter`
- Script `psql-production.sh` com timezone SP
- Views diagnósticas no banco (`v_messages_sp`, `v_conversations_sp`) — migration 014

### [1.5.7] - 2026-02-28

**Security**
- RLS habilitado em `alembic_version` (migration 013)

### [1.5.6] - 2026-02-28

**Security**
- RLS habilitado em `ongs`, `conversations`, `messages` com política `anon_select_ongs` (migration 012)

### [1.5.5] - 2026-02-28

**Security**
- Rate limiting persistente via banco de dados (substitui janela in-memory)
- Circuit breaker por "Fora do Escopo" consecutivo
- Expansão das assinaturas de bot — Fase 2

### [1.5.4] - 2026-02-28

**Security**
- Rate limiting por telefone (janela deslizante)
- Detecção de bot por auto-identificação
- Limite de tentativas na coleta de nome (3 tentativas)

### [1.5.3] - 2026-02-28

**Added**
- Feedback para mensagens de mídia (áudio, vídeo, imagem, documento, sticker)

### [1.5.2] - 2026-02-28

**Fixed**
- Respostas duplicadas: deduplicação de webhooks via `messageId` (migration 010)

### [1.5.1] - 2026-02-28

**Removed**
- Coleta de email removida do fluxo conversacional (migration 008)

### [1.5.0] - 2026-02-28

**Added**
- 275 ONGs parceiras (expansão via seeds v2 e v3)
- `data/seed_ongs_v2.sql`: 33 novas ONGs curadas manualmente
- `data/seed_ongs_v3.sql`: 223 ONGs da ABONG (scraper automatizado)

**Removed**
- Campo `donation_url` removido da tabela `ongs` (migration 007)

### [1.4.1] - 2026-02-28

**Added**
- Estágio `greeting`: na primeira interação, o agente se apresenta como DoaZap e solicita o nome

### [1.4.0] - 2026-02-27

**Added**
- Coleta de perfil do usuário (nome) nas primeiras interações
- Nó `profile_node` no pipeline LangGraph
- Guard-rails contra uso indevido: intent "Fora do Escopo"

### [1.3.0] - 2026-02-23

**Added**
- Integração com New Relic APM
- `POST /api/health` para monitor sintético

### [1.2.0] - 2026-02-10

**Added**
- Memória conversacional: histórico injetado nos prompts

### [1.0.0] - 2026-02-08

Release inicial com todas as funcionalidades do DoaZap: webhook Z-API, agente LangGraph com RAG/FAISS, CRUD de ONGs, autenticação por API Key, migrations Alembic, containerização Docker, suite de testes.

---

## Licença

MIT
