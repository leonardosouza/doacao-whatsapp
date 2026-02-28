[← Voltar ao README](../README.md)

# Observabilidade e Troubleshooting

O banco de dados armazena todos os timestamps em **UTC** (padrão correto para sistemas distribuídos). Para facilitar a correlação de eventos durante incident response, a equipe (fuso horário: São Paulo, UTC-3) conta com três ferramentas de exibição em horário local.

## Logs do Render

Os logs da aplicação são formatados em horário de São Paulo via `_SPFormatter` em `app/main.py`. Exemplo:

```
2026-02-28 14:46:19,475 [INFO] app.api.routes.webhook: Mensagem processada
# (horário SP — armazenado como 17:46:19 UTC no banco)
```

## psql com Timezone SP

O script `scripts/psql-production.sh` conecta ao banco de produção com `timezone=America/Sao_Paulo`. Todos os campos `timestamptz` são exibidos automaticamente em horário SP, sem precisar de `AT TIME ZONE` manual.

```bash
# Conectar ao banco
./scripts/psql-production.sh

# Executar query direta
./scripts/psql-production.sh -c "SELECT * FROM v_messages_sp LIMIT 10;"
```

## Views Diagnósticas no Banco

Disponíveis no **Supabase Table Editor** e via psql para incident response rápido:

| View | Colunas principais |
|------|--------------------|
| `v_messages_sp` | `phone_number`, `direction`, `content`, `intent`, `created_at_sp` |
| `v_conversations_sp` | `phone_number`, `status`, `user_name`, `started_at_sp`, `last_message_at_sp` |

> Acesso restrito ao superusuário `postgres`. Nenhum GRANT concedido a `anon` ou `authenticated`.

## Exportar Diagrama do Grafo LangGraph

O script `scripts/generate_graph.py` gera um PNG do grafo do agente usando a API Mermaid.ink integrada ao LangGraph.

```bash
# Executar a partir da raiz do projeto
python scripts/generate_graph.py
# Saída: generate_graph.png (na pasta atual)
```

A imagem gerada está versionada em [`docs/agent_graph.png`](agent_graph.png).

---

[← Voltar ao README](../README.md)
