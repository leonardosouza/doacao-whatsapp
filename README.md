# DoaçãoBot - Assistente de Doações via WhatsApp

Plataforma de impacto social que conecta doadores à ONG **Mãos que Ajudam** através de uma experiência conversacional no WhatsApp, utilizando IA com LangGraph e RAG.

## Sobre o Projeto

O DoaçãoBot permite que usuários interajam via WhatsApp para:

- **Fazer doações** — receber dados bancários, PIX e orientações
- **Buscar ajuda** — ser encaminhado para assistência social
- **Ser voluntário** — conhecer oportunidades de voluntariado
- **Obter informações** — saber mais sobre a ONG e seus projetos
- **Parcerias corporativas** — conectar empresas à causa

## Stack Tecnológica

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.11+ |
| Framework Web | FastAPI |
| Motor de Conversação | LangGraph |
| LLM | OpenAI GPT-4o |
| Embeddings/RAG | OpenAI Embeddings + FAISS |
| Banco de Dados | PostgreSQL 16 |
| ORM | SQLAlchemy + Alembic |
| Containerização | Docker + Docker Compose |
| WhatsApp | Z-API |

## Estrutura do Projeto

```
doacao-whatsapp/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py             # Configurações
│   ├── api/routes/           # Endpoints (webhook, health)
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Z-API e conversation services
│   ├── agent/                # LangGraph (grafo, nós, estado)
│   └── rag/                  # RAG (loader, retriever)
├── data/
│   └── BASE_INTERACTION.json # Base de conhecimento
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Como Executar

```bash
# Clone o repositório
git clone https://github.com/leonardosouza/doacao-whatsapp.git
cd doacao-whatsapp

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# Execute com Docker
docker compose up --build
```

## Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `OPENAI_API_KEY` | Chave da API OpenAI |
| `ZAPI_INSTANCE_ID` | ID da instância Z-API |
| `ZAPI_TOKEN` | Token de autenticação Z-API |
| `ZAPI_CLIENT_TOKEN` | Client token do Z-API |
| `DATABASE_URL` | URL de conexão PostgreSQL |

## Licença

MIT
