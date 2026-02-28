import logging

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
# Camada 2: Detecção de bots por auto-identificação na mensagem
# ---------------------------------------------------------------------------
_BOT_SIGNATURES = [
    # Fase 1 (v1.5.4)
    "sou a analista virtual",
    "sou um assistente virtual",
    "sou um atendente virtual",
    "analista virtual da ",
    "atendente virtual da ",
    "posso te ajudar com diversos assuntos",
    "informe o seu cpf ou cnpj",
    # Fase 2 (novos padrões CPFL / CRM / NPS)
    "vou verificar se há alguma mensagem",
    "desculpe, não entendi isso",
    "qual é o seu nível de satisfação",
    "link de pagamento gerado",
    "queremos saber sua opinião",
    "número de protocolo",
    "já encontrei seu cadastro",
]


def _is_bot_message(text: str) -> bool:
    """Retorna True se a mensagem contém assinatura típica de bot automatizado."""
    t = text.lower()
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

    # Camada 1: Rate limiting persistente via DB — sem resposta (silêncio quebra loops de bot)
    if conversation_service.count_recent_inbound(db, payload.phone, _RATE_WINDOW) >= _RATE_LIMIT:
        logger.warning(f"Rate limit DB excedido para {_mask_phone(payload.phone)} — mensagem ignorada")
        return {"status": "ignored", "reason": "rate_limited"}

    message_text = payload.get_message_text()
    if not message_text:
        return {"status": "ignored", "reason": "no text content"}

    # Camada 2: Detecção de bot por auto-identificação — sem resposta
    if _is_bot_message(message_text):
        logger.warning(f"Bot detectado em {_mask_phone(payload.phone)}: {_truncate_msg(message_text)!r}")
        return {"status": "ignored", "reason": "bot_detected"}

    if conversation_service.is_duplicate_message(db, payload.messageId):
        logger.warning(f"Webhook duplicado ignorado: messageId={payload.messageId}")
        return {"status": "ignored", "reason": "duplicate"}

    # Camada 3: Circuit breaker OOS — silencia após 3 respostas consecutivas fora do escopo
    if conversation_service.has_consecutive_out_of_scope(db, payload.phone):
        logger.warning(f"OOS consecutivo detectado para {_mask_phone(payload.phone)} — silêncio ativado")
        return {"status": "ignored", "reason": "consecutive_oos"}

    logger.info(f"Mensagem recebida de {_mask_phone(payload.phone)}: {_truncate_msg(message_text)}")

    conversation = conversation_service.get_or_create_conversation(
        db, payload.phone
    )

    inbound_msg = conversation_service.save_message(
        db,
        conversation=conversation,
        direction="inbound",
        content=message_text,
        zapi_message_id=payload.messageId,
    )

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
