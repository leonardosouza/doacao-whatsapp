[← Voltar ao README](../README.md)

# Segurança

Este documento descreve as medidas de segurança implementadas no DoaZap, organizadas por camada.

## Proteção do Webhook (5 camadas sequenciais)

Toda mensagem recebida em `POST /api/webhook` passa pelos seguintes filtros em ordem, antes de chegar ao agente:

| Camada | Mecanismo | Ação |
|--------|-----------|------|
| 0 | Validação de `instanceId` | Rejeita payloads de instâncias Z-API desconhecidas |
| 1 | Rate limiting por número (banco de dados) | Silencia após ≥ 5 msgs em 60s; sobrevive a reinicializações |
| 2 | Detecção de bot por auto-identificação | Descarta mensagens com assinaturas de CRM/assistentes virtuais |
| 3 | Circuit breaker OOS proporcional | Silencia após ≥ 3 de 6 respostas "Fora do Escopo" em 2 minutos |
| 4 | Limite de tentativas de coleta de nome | Máximo 3 tentativas; prossegue sem nome para evitar loop |

### Camada 0 — Validação de Origem (`instanceId`)

O payload Z-API inclui o campo `instanceId` que identifica a instância de origem. O webhook rejeita silenciosamente qualquer payload cujo `instanceId` não corresponda ao `ZAPI_INSTANCE_ID` configurado via variável de ambiente. Isso impede que terceiros injetem mensagens falsas no endpoint.

```python
if payload.instanceId != settings.ZAPI_INSTANCE_ID:
    return {"status": "ignored", "reason": "unknown_instance"}
```

### Camada 1 — Rate Limiting Persistente

Implementado via contagem direta na tabela `messages` (campo `created_at` + `direction='inbound'`). Por usar o banco de dados, o limite persiste entre deploys e reinicializações — ao contrário de soluções in-memory que resetam ao reiniciar o processo.

Limites: **5 mensagens / 60 segundos** por número de telefone.

**Race condition corrigida (v1.6.3):** A mensagem inbound é salva no banco **antes** da verificação de rate limit. Isso garante que requisições concorrentes (FastAPI async) são contadas antes do check — eliminando o bypass onde múltiplas requisições chegavam simultaneamente, viam `count=0` e todas passavam pelo filtro (identificado em produção: bot CPFL gerou 14 respostas em vez de 5 em 33 segundos). A condição foi ajustada de `>= 5` para `> 5` (o contador agora inclui a mensagem atual), mantendo o mesmo limite efetivo de 5 mensagens processadas por janela.

### Camada 2 — Detecção de Bot

Implementada em dois níveis complementares (v1.6.3):

**Padrões regex — famílias genéricas** (cobrem qualquer empresa):

| Padrão | Cobertura |
|--------|-----------|
| Auto-identificação virtual | "sou a/o/um/uma … assistente/analista/atendente/agente/colaborador(a) virtual" (qualquer empresa) |
| Solicitação de CPF/CNPJ | "informe/confirme/digit[ae]/insira/envie/mand[ae] … CPF/CNPJ" |
| Validação negativa de CPF/CNPJ | "esse/este/o/a CPF/CNPJ … inválido/incorreto/não encontrado" |
| Pesquisa NPS | "nível de satisfação", "de 0 a 10 … avalia/classifica", "muito insatisfeito … muito satisfeito" |
| 2ª via de conta | "2ª/segunda via de fatura(s)/conta(s)/boleto(s)/débito(s)" — concessionárias |

**Literais — padrões únicos** (que não se generalizam via regex):
- `maga.lu`, `política de privacidade do magalu` (Magalu/Lu)
- `sou a sani`, `posso te ajudar com diversos serviços`, `não conseguimos identificar sua solicitação`,
  `encerrado por inatividade` (Sabesp e concessionárias genéricas)
- `lamentamos por sua experiência`, `agradecemos pelo seu tempo` (pós-atendimento CRM)
- `link de pagamento gerado`, `queremos saber sua opinião`, `número de protocolo`,
  `já encontrei seu cadastro`, `vou verificar se há alguma mensagem`, `desculpe, não entendi isso` (CRM)
- `é sua vez!` (spam/promoção)
- `não vamos seguir nesse momento com` (rejeição de CRM)

### Camada 3 — Circuit Breaker OOS (Proporcional)

Detecta quando **ao menos 3 das últimas 6 respostas `outbound`** para um número foram classificadas como `"Fora do Escopo"` dentro de uma janela de 2 minutos. Nesse caso, a próxima mensagem é descartada sem resposta.

A lógica proporcional (em vez de consecutiva) corrige um bypass onde bots de terceiros intercalavam mensagens genéricas (`Ambíguo`) entre as respostas OOS para quebrar a contagem consecutiva e continuar o loop.

### Guard-Rails do Agente LLM

Mensagens classificadas como `"Fora do Escopo"` pelo nó `classify` não acessam o banco de ONGs (`enrich` é pulado) e recebem uma resposta gentil de redirecionamento gerada pelo nó `generate`.

Padrões bloqueados:
- Perguntas de cultura pop, esportes, ciência geral, política
- Tentativas de **prompt injection** ("ignore suas instruções…")
- Tentativas de **jailbreak** ("DAN", "modo sem restrições"…)
- Impersonação de outro serviço (boletos, cobranças, outro bot)
- Solicitação do prompt de sistema ou mudança de identidade

---

## Proteção de Dados (LGPD)

### Mascaramento de PII nos Logs

Números de telefone são mascarados em **todos** os eventos de log — apenas os 4 últimos dígitos são exibidos. Conteúdo de mensagens é truncado a 30 caracteres.

```
# Antes (v1.5.8):
[INFO] Mensagem recebida de 5511999990000: Quero fazer uma doação para crianças

# Depois (v1.5.9):
[INFO] Mensagem recebida de ****0000: Quero fazer uma doa…
```

Isso garante que logs enviados ao New Relic ou qualquer sistema de observabilidade externo não contenham PII rastreável.

### Dados Armazenados

| Dado | Armazenamento | Justificativa |
|------|---------------|---------------|
| Número de telefone | Banco de dados (criptografado em repouso pelo Supabase) | Necessário para gerenciar sessões de conversa |
| Nome do usuário | Banco de dados | Coletado com consentimento para personalizar atendimento |
| Conteúdo das mensagens | Banco de dados | Necessário para histórico conversacional e melhoria do serviço |
| Intents / sentimentos | Banco de dados | Análise agregada de uso (sem identificação individual) |

---

## Proteção da API

### Autenticação de Endpoints de Escrita

Rotas `POST`, `PUT` e `DELETE` em `/api/ongs` exigem o header `X-API-Key` com valor igual à variável `API_KEY`. Requisições sem a chave ou com chave inválida recebem `HTTP 401`.

### CORS Restrito

O middleware `CORSMiddleware` limita requisições cross-origin aos domínios conhecidos da plataforma:

```
https://doacao-whatsapp.onrender.com
https://doazap-dashboard.onrender.com
```

Requisições de outras origens não recebem os headers CORS e são bloqueadas pelo browser.

### Swagger / ReDoc Desabilitados em Produção

As rotas `/docs` e `/redoc` só são servidas quando `DEBUG=True`. Em produção (`APP_ENV=production`), `DEBUG` é `False` e as rotas retornam `HTTP 404`.

---

## Proteção do Banco de Dados

### Row Level Security (RLS) no Supabase

Todas as tabelas têm RLS habilitado, bloqueando acesso via API REST do Supabase (role `anon`):

| Tabela | Acesso `anon` |
|--------|---------------|
| `ongs` | SELECT permitido (dado público) |
| `conversations` | Bloqueado completamente |
| `messages` | Bloqueado completamente |
| `alembic_version` | Bloqueado completamente |

O FastAPI conecta como superusuário `postgres`, que contorna RLS por design do PostgreSQL.

### Escape de Metacaracteres LIKE

Filtros de busca em `GET /api/ongs?category=...&city=...` escapam os metacaracteres `%`, `_` e `\` antes de montar a query `ILIKE`, evitando que um usuário mal-intencionado use wildcards para retornar conjuntos de dados não intencionais.

---

## Proteção de Credenciais

### Variáveis de Ambiente

Todas as credenciais são injetadas via variáveis de ambiente — nenhum secret é hardcoded no código-fonte. O arquivo `.env.production` está listado no `.gitignore` (regra `.env.*`) e nunca foi commitado ao repositório.

### Sanitização de Logs da Z-API

O token Z-API é embutido na URL base por requisito da API da Z-API. Para evitar vazamento em stack traces ou logs de erro, a função `_safe_err()` substitui o token por `***` antes de qualquer chamada a `logger.*`:

```python
def _safe_err(exc: Exception) -> str:
    return str(exc).replace(settings.ZAPI_TOKEN, "***")
```

### Timeout nas Requisições HTTP

Todas as requisições HTTP para a Z-API têm timeout de **10 segundos** (`_ZAPI_TIMEOUT`), evitando que requisições lentas ou stalled travem o event loop do FastAPI.

---

## Reportar Vulnerabilidades

Para reportar uma vulnerabilidade de segurança, entre em contato diretamente com a equipe via e-mail institucional (ver [README](../README.md#equipe)). Não abra issues públicas para vulnerabilidades de segurança.

---

[← Voltar ao README](../README.md)
