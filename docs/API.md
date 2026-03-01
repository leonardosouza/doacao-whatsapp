[← Voltar ao README](../README.md)

# API Reference

## Endpoints

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

## GET /api/ongs — Parâmetros de Busca

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

## Autenticação

Rotas de escrita (POST, PUT, DELETE em `/api/ongs`) exigem o header:

```
X-API-Key: sua-api-key-secreta
```

## Health Check

```bash
curl https://doacao-whatsapp.onrender.com/api/health
# {"status": "ok", "database": "connected", "zapi": "connected"}
```

---

[← Voltar ao README](../README.md)
