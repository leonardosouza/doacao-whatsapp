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

Detalhes completos em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): fluxo de mensagens, grafo LangGraph, intents suportados e guard-rails de segurança.

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
│   ├── seed_ongs_v2.sql         # Seed original (52 ONGs, 2026-02-28)
│   └── seed_ongs_v3.sql         # Seed ABONG (223 novas ONGs, total: 275)
├── tests/                       # 192 testes automatizados (99% cobertura)
├── docs/
│   ├── agent_graph.png          # Diagrama visual do grafo LangGraph
│   ├── ARCHITECTURE.md          # Arquitetura, fluxo e guard-rails
│   ├── API.md                   # Referência de endpoints
│   ├── CONFIGURATION.md         # Setup, variáveis de ambiente e RLS
│   ├── DEPLOY.md                # Deploy no Render e New Relic
│   ├── TESTING.md               # Testes unitários e de carga
│   ├── OBSERVABILITY.md         # Logs, psql timezone e views diagnósticas
│   └── SECURITY.md              # Medidas de segurança e proteção de dados (LGPD)
├── docker-compose.yml           # App + PostgreSQL
├── Dockerfile                   # Python 3.13-slim
├── alembic.ini
├── pyproject.toml               # Configuração pytest
├── requirements.txt
└── .env.example
```

## Quick Start

```bash
git clone https://github.com/leonardosouza/doacao-whatsapp.git
cd doacao-whatsapp
cp .env.example .env.development
# edite .env.development com suas credenciais
docker compose up --build
docker compose exec app alembic upgrade head
```

Para instruções detalhadas de configuração e variáveis de ambiente, consulte [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Documentação

| Documento | Descrição |
|-----------|-----------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Fluxo de mensagens, grafo LangGraph, intents e guard-rails |
| [API.md](docs/API.md) | Referência completa dos endpoints |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | Pré-requisitos, setup, variáveis de ambiente e RLS |
| [DEPLOY.md](docs/DEPLOY.md) | Deploy no Render, monitoramento New Relic e synthetics |
| [TESTING.md](docs/TESTING.md) | Testes unitários, cobertura e testes de carga |
| [OBSERVABILITY.md](docs/OBSERVABILITY.md) | Logs, psql timezone e views diagnósticas |
| [SECURITY.md](docs/SECURITY.md) | Camadas de segurança, LGPD e proteção de credenciais |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de versões |

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
