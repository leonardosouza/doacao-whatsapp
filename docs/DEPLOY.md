[← Voltar ao README](../README.md)

# Deploy em Produção

A aplicação está hospedada no [Render](https://render.com/) com banco de dados [Supabase](https://supabase.com/).

## Infraestrutura

| Serviço | Plataforma |
|---------|------------|
| Aplicação (FastAPI) | Render (Web Service) |
| Banco de Dados (PostgreSQL) | Supabase (Connection Pooler) |
| Monitoramento / APM | New Relic |

## Configuração

1. Crie um Web Service no Render apontando para este repositório
2. Configure as variáveis de ambiente no painel do Render (mesmas do `.env.production`)
3. Para o `DATABASE_URL`, utilize a connection string do Supabase (pooler)
4. Configure as variáveis `NEW_RELIC_LICENSE_KEY` e `NEW_RELIC_APP_NAME` no Render
5. Configure o webhook no Z-API apontando para `https://doacao-whatsapp.onrender.com/api/webhook`

O agente New Relic é iniciado automaticamente via `newrelic-admin run-program` (definido no `Dockerfile`), sem necessidade de arquivo de configuração no repositório.

## Health Check

```bash
curl https://doacao-whatsapp.onrender.com/api/health
# {"status": "ok", "database": "connected", "zapi": "connected"}
```

## Monitoramento (New Relic APM)

| Ambiente | URL |
|----------|-----|
| Produção (`DoaZap`) | [one.newrelic.com → APM & Services → DoaZap](https://one.newrelic.com/apm) |
| Desenvolvimento (`DoaZap (Dev)`) | [one.newrelic.com → APM & Services → DoaZap (Dev)](https://one.newrelic.com/apm) |

> O ambiente de desenvolvimento só aparece no New Relic enquanto a aplicação local estiver rodando com as variáveis `NEW_RELIC_*` configuradas no `.env.development`.

## Monitor Sintético (New Relic Synthetics)

O endpoint `POST /api/health` está disponível para uso com o [New Relic Synthetics](https://one.newrelic.com/synthetics):

```
https://doacao-whatsapp.onrender.com/api/health
Método: POST
```

## Deploy Forçado via API

Para disparar um deploy manualmente no Render:

```bash
curl -s -X POST "https://api.render.com/v1/services/{SERVICE_ID}/deploys" \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"clearCache": "do_not_clear"}'
```
