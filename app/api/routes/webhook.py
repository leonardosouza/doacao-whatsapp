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


@router.post("/webhook", response_model=WebhookResponse)
async def receive_webhook(payload: ZAPIWebhookPayload, db: Session = Depends(get_db)):
    if payload.fromMe or payload.isGroup:
        return {"status": "ignored"}

    message_text = payload.get_message_text()
    if not message_text:
        return {"status": "ignored", "reason": "no text content"}

    logger.info(f"Mensagem recebida de {payload.phone}: {message_text}")

    conversation = conversation_service.get_or_create_conversation(
        db, payload.phone
    )

    inbound_msg = conversation_service.save_message(
        db,
        conversation=conversation,
        direction="inbound",
        content=message_text,
    )

    # Recupera histórico da conversa para contexto do agente (exclui a mensagem atual)
    history_messages = conversation_service.get_conversation_history(
        db, conversation, limit=settings.CONVERSATION_HISTORY_LIMIT,
        exclude_message_id=inbound_msg.id,
    )
    conversation_history = conversation_service.format_history(history_messages)

    # Processa mensagem pelo agente LangGraph
    result = await process_message(message_text, db, conversation_history=conversation_history)
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
