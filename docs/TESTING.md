# Testes

O projeto possui **162 testes automatizados** com **99% de cobertura**, utilizando SQLite in-memory para isolamento completo (sem dependências externas).

## Executar os Testes

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

## Estrutura dos Testes

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

## Cobertura por Módulo

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
