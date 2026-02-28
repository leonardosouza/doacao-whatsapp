# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adota o [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.5.3] - 2026-02-28

### Added
- **Feedback para mensagens de mídia**: ao receber áudio, vídeo, imagem, documento ou sticker,
  o bot responde com uma mensagem amigável explicando que apenas texto é suportado
- Novos modelos Pydantic no schema do webhook: `AudioContent`, `VideoContent`, `ImageContent`,
  `DocumentContent`, `StickerContent`
- Método `get_media_type()` em `ZAPIWebhookPayload` detecta o tipo de mídia recebido
- 13 novos testes (6 de schema, 6 de handler, 1 de isolamento do agente) — total: 144 testes

---

## [1.5.2] - 2026-02-28

### Fixed
- **Respostas duplicadas**: deduplicação de webhooks via `messageId` do Z-API
  - Campo `zapi_message_id` (unique) adicionado à tabela `messages`
  - Webhook handler retorna `ignored/duplicate` imediatamente se o `messageId` já foi processado
  - Elimina respostas duplas causadas por reentrega do Z-API quando o servidor demora a responder

### Infrastructure
- Migration 010: `ADD COLUMN zapi_message_id VARCHAR(100) UNIQUE TO messages`

---

## [1.5.1] - 2026-02-28

### Removed
- Etapa de coleta de email removida do fluxo conversacional (decisão de UX)
- Fluxo simplificado: `greeting → collecting_name → complete` (antes passava por `collecting_email`)
- Campo `user_email` removido da tabela `conversations`, model SQLAlchemy e estado do agente
- Parâmetro `user_email` removido de `update_user_profile()` em `conversation_service`
- 13 testes relacionados a coleta de email removidos (127 testes, 99% cobertura)

### Infrastructure
- Migration 008: `DROP COLUMN user_email FROM conversations`

---

## [1.5.0] - 2026-02-28

### Added
- **52 ONGs parceiras**: expansão da base de 19 para 52 ONGs via seed do `ONGS_v2.csv`,
  cobrindo novas categorias (LGBTQIA+, Mulheres, Inclusão Produtiva, Cultura,
  Pessoas com Deficiência) e novos estados (AM, BA, CE, DF, MS, PA, PB, PR, RS, RN, MG, SC)
- `data/seed_ongs_v2.sql`: seed com 33 novas ONGs (duplicatas já existentes excluídas)

### Removed
- Campo `donation_url` removido da tabela `ongs`, model SQLAlchemy, schemas Pydantic
  e lógica do agente

### Changed
- Query de filtragem para intent "Quero Doar" simplificada: usa apenas `pix_key` e `bank_info`
- `_format_ong`: linha "Doação: ..." removida da formatação exibida ao usuário
- Testes atualizados para refletir a remoção de `donation_url` (140 testes, 99% cobertura)

### Infrastructure
- Migration 007: `DROP COLUMN donation_url FROM ongs`

---

## [1.4.1] - 2026-02-28

### Added
- **Estágio `greeting`**: na primeira interação, o agente se apresenta como DoaZap
  (missão, serviços e ONGs parceiras), reconhece brevemente a intenção do usuário e
  já solicita o nome — tudo em um único turno, mantendo o onboarding em 2 rodadas
- Detecção de primeira interação por `last_bot_content is None` no `make_profile_node`
- `route_profile` estendido para rotear `"greeting"` → `profile_response_node`
- 2 novos testes automatizados (140 testes no total)

### Changed
- `PROFILE_COLLECT_PROMPT` atualizado com instruções detalhadas para o estágio `greeting`
- `profile_stage` agora segue a sequência: `greeting → collecting_name → collecting_email → complete`
- Teste `test_collecting_name_on_first_interaction` atualizado para refletir novo comportamento

---

## [1.4.0] - 2026-02-27

### Added
- **Coleta de perfil do usuário**: agente coleta nome e email nas primeiras interações,
  associando-os ao número de telefone. Uma vez persistidos, nunca são solicitados novamente
- Novo nó `profile_node` no início do pipeline LangGraph com roteamento condicional:
  coleta nome → coleta email → atendimento normal
- `profile_response_node` gera perguntas empáticas via LLM (tom WhatsApp)
- Extração de nome via LLM (`EXTRACT_NAME_PROMPT`) e email via regex (sem custo adicional de LLM)
- Helpers `_bot_asked_for_name`, `_bot_asked_for_email`, `_extract_email_from_text`
  detectam contexto da última interação para saber o que foi perguntado
- Migration 003: colunas `user_name` e `user_email` na tabela `conversations`
- `update_user_profile()` no `conversation_service` para persistência dos dados coletados
- **Guard-rails contra uso indevido**: novo intent "Fora do Escopo" com regras explícitas
  para pop culture, esportes, jailbreak, impersonation de bots e prompt injection
- Seção `LIMITES E SEGURANÇA` no `GENERATE_PROMPT` com instrução de recusa gentil
- Retorno antecipado no `enrich_node` para "Fora do Escopo" (zero queries ao banco)
- 7 exemplos reais de interações indevidas adicionados à base RAG (BASE_INTERACTION.json),
  baseados em análise do banco de produção
- 26 novos testes automatizados (138 testes no total, 99%+ de cobertura)

## [1.3.1] - 2026-02-24

### Fixed
- Adicionados testes para `POST /api/health` (cobertura de 97% → 100% em `health.py`)

## [1.3.0] - 2026-02-23

### Added
- Integração com New Relic APM para monitoramento de performance em produção
- Instrumentação automática via `newrelic-admin run-program` (sem arquivo de configuração no repositório)
- Variáveis `NEW_RELIC_*` documentadas no `.env.example`
- Monitoramento automático de requisições HTTP, queries SQL, chamadas externas (OpenAI, Z-API) e erros
- Suporte a `POST /api/health` para uso com monitor sintético do New Relic Synthetics

## [1.2.0] - 2026-02-10

### Added
- Memória conversacional: agente mantém contexto entre mensagens do mesmo usuário
- Histórico das últimas mensagens injetado nos prompts de classificação e geração
- Configuração `CONVERSATION_HISTORY_LIMIT` para limitar mensagens no histórico
- Funções `get_conversation_history` e `format_history` no conversation_service
- 104 testes automatizados com 99% de cobertura

## [1.1.1] - 2026-02-08

### Fixed
- Adicionar `response_model` nas rotas health e webhook para exibição correta no Swagger

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
