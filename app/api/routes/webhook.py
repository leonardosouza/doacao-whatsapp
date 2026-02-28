import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.graph import process_message
from app.config import settings
from app.database import get_db
from app.schemas.webhook import WebhookResponse, ZAPIWebhookPayload
from app.services import conversation_service, zapi_service

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Camada 1: Rate limiting por telefone (janela deslizante em memória)
# ---------------------------------------------------------------------------
_rate_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 12   # máximo de mensagens por janela
_RATE_WINDOW = 60  # janela em segundos


def _is_rate_limited(phone: str) -> bool:
    """Retorna True se o telefone excedeu o limite de mensagens na janela atual."""
    now = time.time()
    cutoff = now - _RATE_WINDOW
    timestamps = [t for t in _rate_store[phone] if t > cutoff]
    timestamps.append(now)
    _rate_store[phone] = timestamps
    return len(timestamps) > _RATE_LIMIT


# ---------------------------------------------------------------------------
# Camada 2: Detecção de bots por auto-identificação na mensagem
# ---------------------------------------------------------------------------
_BOT_SIGNATURES = [
    "sou a analista virtual",
    "sou um assistente virtual",
    "sou um atendente virtual",
    "analista virtual da ",
    "atendente virtual da ",
    "posso te ajudar com diversos assuntos",
    "informe o seu cpf ou cnpj",
]


def _is_bot_message(text: str) -> bool:
    """Retorna True se a mensagem contém assinatura típica de bot automatizado."""
    t = text.lower()
    return any(sig in t for sig in _BOT_SIGNATURES)


@router.post("/webhook", response_model=WebhookResponse)
async def receive_webhook(payload: ZAPIWebhookPayload, db: Session = Depends(get_db)):
    if payload.fromMe or payload.isGroup:
        return {"status": "ignored"}

    media_type = payload.get_media_type()
    if media_type:
        logger.info(f"Mídia recebida ({media_type}) de {payload.phone} — enviando aviso ao usuário")
        await zapi_service.send_text_message(
            payload.phone,
            "Oi! 😊 Por enquanto só consigo processar mensagens de texto. "
            "Escreva sua mensagem e terei prazer em ajudar! 🤝",
        )
        return {"status": "unsupported_media", "reason": media_type}

    # Camada 1: Rate limiting — sem resposta ao remetente (silêncio quebra loops de bot)
    if _is_rate_limited(payload.phone):
        logger.warning(f"Rate limit excedido para {payload.phone} — mensagem ignorada")
        return {"status": "ignored", "reason": "rate_limited"}

    message_text = payload.get_message_text()
    if not message_text:
        return {"status": "ignored", "reason": "no text content"}

    # Camada 2: Detecção de bot por auto-identificação — sem resposta
    if _is_bot_message(message_text):
        logger.warning(f"Bot detectado em {payload.phone}: {message_text[:80]!r}")
        return {"status": "ignored", "reason": "bot_detected"}

    if conversation_service.is_duplicate_message(db, payload.messageId):
        logger.warning(f"Webhook duplicado ignorado: messageId={payload.messageId}")
        return {"status": "ignored", "reason": "duplicate"}

    logger.info(f"Mensagem recebida de {payload.phone}: {message_text}")

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
        f"Resposta enviada para {payload.phone} "
        f"[intent={result['intent']}, sentiment={result['sentiment']}]"
    )

    return {"status": "processed", "intent": result["intent"]}
