[← Voltar ao README](../README.md)

# API Reference

## Endpoints

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
