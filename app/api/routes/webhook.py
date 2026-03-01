import logging
import re

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.graph import process_message
from app.config import settings
from app.database import get_db
from app.schemas.webhook import WebhookResponse, ZAPIWebhookPayload
from app.services import conversation_service, zapi_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _mask_phone(phone: str) -> str:
    """Mascara número de telefone para logs — preserva apenas os 4 últimos dígitos."""
    digits = "".join(c for c in phone if c.isdigit())
    return f"****{digits[-4:]}" if len(digits) >= 4 else "****"


def _truncate_msg(text: str, max_len: int = 30) -> str:
    """Trunca conteúdo de mensagem para logs — evita expor PII."""
    return text[:max_len] + "…" if len(text) > max_len else text

# ---------------------------------------------------------------------------
# Camada 1: Rate limiting persistente via banco de dados (5 msgs/60s)
# ---------------------------------------------------------------------------
_RATE_LIMIT = 5    # máximo de mensagens por janela
_RATE_WINDOW = 60  # janela em segundos

# ---------------------------------------------------------------------------
# Camada 2: Detecção de bots — padrões regex (famílias genéricas) + literais
# ---------------------------------------------------------------------------

# Padrões regex: cobrem famílias inteiras de bots sem depender de nomes de empresa
_BOT_PATTERNS: list[re.Pattern] = [
    # 1. Auto-identificação como assistente/analista/atendente virtual (qualquer empresa)
    #    Cobre: "Sou a analista virtual da CPFL", "Aqui é a Lu, assistente virtual do Magalu",
    #           "Sou o assistente virtual da Sabesp", "Eu sou um atendente virtual",
    #           "Me chamo Bia, colaboradora virtual da XP"
    re.compile(
        r"\b(sou [ao]|sou uma?|aqui [eé] [ao]|eu sou [ao]|eu sou uma?|me chamo)"
        r".{0,80}\b(assistente|analista|atendente|colaboradora?|agente)\s+virtual\b",
        re.IGNORECASE | re.DOTALL,
    ),
    # 2. Solicitação de CPF ou CNPJ (qualquer empresa ou fluxo de validação)
    #    Cobre: "Informe seu CPF", "Confirme seu CNPJ", "Digite seu CPF para continuar",
    #           "Insira o CPF ou CNPJ", "Por favor, mande o seu CPF"
    re.compile(
        r"\b(informe|confirme|digit[ae]|insira|passe|envie|mand[ae])\b.{0,60}\b(cpf|cnpj)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    # 3. Validação negativa de CPF/CNPJ — loop típico de bot que rejeita o input
    #    Cobre: "Esse CPF não é válido", "O CNPJ informado não é válido",
    #           "Esse CPF ou CNPJ está incorreto", "CPF inválido, tente novamente"
    re.compile(
        r"\b(esse|este|o|a)\s+(cpf|cnpj)\b.{0,60}"
        r"\b(válido|inválido|incorreto|não\s+existe|não\s+encontrado)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(cpf|cnpj)\b.{0,40}\b(inválido|incorreto|não\s+encontrado|não\s+existe)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    # 4. Pesquisa NPS / satisfação (pós-atendimento automático)
    #    Cobre: "Qual é o seu nível de satisfação?", "De 0 a 10, como você avalia?",
    #           "Muito insatisfeito | Insatisfeito | Neutro | Satisfeito | Muito satisfeito"
    re.compile(r"\bn[íi]vel\s+de\s+satisfa[çc][aã]o\b", re.IGNORECASE),
    re.compile(
        r"\bmuito\s+insatisfeito\b.{0,80}\bmuito\s+satisfeito\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bde\s+[0-9]\s+a\s+10\b.{0,60}\b(avalia|classifica|nota|pontua)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    # 5. Oferta de 2ª via de conta (concessionárias de água, energia, gás, telefonia)
    #    Cobre: "2ª via de fatura", "2ª via de faturas", "segunda via da conta",
    #           "Solicite a 2ª via de boleto", "serviço de segunda via de débito"
    re.compile(
        r"\b(2ª?|segunda)\s+via\s+(de\s+)?(faturas?|contas?|boletos?|d[eé]bitos?|servi[çc]os?)\b",
        re.IGNORECASE,
    ),
]

# Literais: padrões únicos que não se generalizam via regex
_BOT_SIGNATURES: list[str] = [
    # Magalu (Lu) — URL encurtada proprietária e política de privacidade
    "maga.lu",
    "política de privacidade do magalu",
    # Sabesp/Sani e concessionárias genéricas
    "sou a sani",
    "posso te ajudar com diversos serviços",
    "não conseguimos identificar sua solicitação",
    "encerrado por inatividade",
    # Pós-atendimento / CRM genérico
    "lamentamos por sua experiência",
    "agradecemos pelo seu tempo",
    "link de pagamento gerado",
    "queremos saber sua opinião",
    "número de protocolo",
    "já encontrei seu cadastro",
    "vou verificar se há alguma mensagem",
    "desculpe, não entendi isso",
    # Spam / promoção
    "é sua vez!",
    # Rejeição de CRM
    "não vamos seguir nesse momento com",
]


def _is_bot_message(text: str) -> bool:
    """Retorna True se a mensagem contém assinatura típica de bot automatizado."""
    t = text.lower()
    # Verifica padrões regex (famílias genéricas de bots)
    if any(pat.search(t) for pat in _BOT_PATTERNS):
        return True
    # Verifica literais (padrões únicos que não se generalizam)
    return any(sig in t for sig in _BOT_SIGNATURES)


@router.post("/webhook", response_model=WebhookResponse)
async def receive_webhook(payload: ZAPIWebhookPayload, db: Session = Depends(get_db)):
    # Camada 0: Valida que o webhook vem da instância Z-API configurada
    if payload.instanceId != settings.ZAPI_INSTANCE_ID:
        logger.warning(f"Webhook rejeitado: instanceId desconhecido ({payload.instanceId!r})")
        return {"status": "ignored", "reason": "unknown_instance"}

    if payload.fromMe or payload.isGroup:
        return {"status": "ignored"}

    media_type = payload.get_media_type()
    if media_type:
        logger.info(f"Mídia recebida ({media_type}) de {_mask_phone(payload.phone)} — enviando aviso ao usuário")
        await zapi_service.send_text_message(
            payload.phone,
            "Oi! 😊 Por enquanto só consigo processar mensagens de texto. "
            "Escreva sua mensagem e terei prazer em ajudar! 🤝",
        )
        return {"status": "unsupported_media", "reason": media_type}

    message_text = payload.get_message_text()
    if not message_text:
        return {"status": "ignored", "reason": "no text content"}

    # Camada 2: Detecção de bot por padrões regex e literais — sem resposta
    if _is_bot_message(message_text):
        logger.warning(f"Bot detectado em {_mask_phone(payload.phone)}: {_truncate_msg(message_text)!r}")
        return {"status": "ignored", "reason": "bot_detected"}

    if conversation_service.is_duplicate_message(db, payload.messageId):
        logger.warning(f"Webhook duplicado ignorado: messageId={payload.messageId}")
        return {"status": "ignored", "reason": "duplicate"}

    # Camada 3: Circuit breaker OOS — silencia após 3 de 6 respostas "Fora do Escopo"
    if conversation_service.has_consecutive_out_of_scope(db, payload.phone):
        logger.warning(f"OOS consecutivo detectado para {_mask_phone(payload.phone)} — silêncio ativado")
        return {"status": "ignored", "reason": "consecutive_oos"}

    logger.info(f"Mensagem recebida de {_mask_phone(payload.phone)}: {_truncate_msg(message_text)}")

    conversation = conversation_service.get_or_create_conversation(
        db, payload.phone
    )

    # Salva a mensagem ANTES do rate limit: o contador inclui a mensagem atual,
    # eliminando o race condition onde requisições concorrentes viam count=0 e
    # todas passavam simultaneamente pelo check (CPFL: 14 respostas em vez de 5).
    inbound_msg = conversation_service.save_message(
        db,
        conversation=conversation,
        direction="inbound",
        content=message_text,
        zapi_message_id=payload.messageId,
    )

    # Camada 1: Rate limiting persistente via DB — count > LIMIT (inclui msg atual)
    if conversation_service.count_recent_inbound(db, payload.phone, _RATE_WINDOW) > _RATE_LIMIT:
        logger.warning(f"Rate limit DB excedido para {_mask_phone(payload.phone)} — mensagem ignorada")
        return {"status": "ignored", "reason": "rate_limited"}

    # Recupera histórico da conversa para contexto do agente (exclui a mensagem atual)
    history_messages = conversation_service.get_conversation_history(
        db, conversation, limit=settings.CONVERSATION_HISTORY_LIMIT,
        exclude_message_id=inbound_msg.id,
    )
    conversation_history = conversation_service.format_history(history_messages)

    # Processa mensagem pelo agente LangGraph
    result = await process_message(
        message_text, db,
        conversation_history=conversation_history,
        conversation=conversation,
    )
    response_text = result["response"]

    conversation_service.save_message(
        db,
        conversation=conversation,
        direction="outbound",
        content=response_text,
        intent=result["intent"],
        sentiment=result["sentiment"],
    )

    await zapi_service.send_text_message(payload.phone, response_text)

    logger.info(
        f"Resposta enviada para {_mask_phone(payload.phone)} "
        f"[intent={result['intent']}, sentiment={result['sentiment']}]"
    )

    return {"status": "processed", "intent": result["intent"]}
