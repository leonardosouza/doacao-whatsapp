# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adota o [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.1.0] - 2026-02-08

### Added
- Testes para cenários de 404 em update/delete de ONGs (89 testes, 99% de cobertura)

### Added (infra)
- CHANGELOG.md seguindo padrão Keep a Changelog

## [1.0.0] - 2026-02-08

Release inicial com funcionalidades completas do DoaZap.

### Added
- Bootstrap FastAPI com health check (database + Z-API)
- Modelos de dados com SQLAlchemy e migrations via Alembic
- Webhook Z-API para recebimento e envio de mensagens WhatsApp
- Camada RAG com FAISS e OpenAI Embeddings
- Agente conversacional LangGraph com classificação, RAG e geração
- Integração completa: webhook → agente → resposta
- CRUD completo de ONGs (modelo, schemas, serviço, rotas REST)
- Nó `enrich` no agente para injetar dados de ONGs do banco
- Script de seed para importar ONGs do JSON
- Split de `.env` por ambiente (development/production)
- Swagger restrito ao ambiente de desenvolvimento
- Proteção de rotas de escrita de ONGs com API Key
- Suite completa de testes automatizados (85 testes, 98% de cobertura)
- Semantic versioning com exposição da versão no health check
- Containerização com Docker e docker-compose

### Changed
- Upgrade do modelo para gpt-4.1-mini
- Renomeação da aplicação para DoaZap
- Reescrita da base RAG com dados reais

### Fixed
- Porta da aplicação alterada de 8000 para 80
- Correção de dependência langchain-community e versão faiss-cpu
- Correção do graph.py com dados reais do projeto
- Aumento do limite de ONGs para intents não filtrados
