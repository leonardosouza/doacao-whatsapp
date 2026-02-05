import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.webhook import ZAPIWebhookPayload
from app.services import conversation_service, zapi_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook")
async def receive_webhook(payload: ZAPIWebhookPayload, db: Session = Depends(get_db)):
    # Ignora mensagens enviadas pelo próprio bot ou de grupos
    if payload.fromMe or payload.isGroup:
        return {"status": "ignored"}

    message_text = payload.get_message_text()
    if not message_text:
        return {"status": "ignored", "reason": "no text content"}

    logger.info(f"Mensagem recebida de {payload.phone}: {message_text}")

    # Busca ou cria conversa
    conversation = conversation_service.get_or_create_conversation(
        db, payload.phone
    )

    # Salva mensagem de entrada
    conversation_service.save_message(
        db,
        conversation=conversation,
        direction="inbound",
        content=message_text,
    )

    # TODO: Integrar com agente LangGraph (commit #7-8)
    response_text = (
        "Olá! Sou o assistente da Mãos que Ajudam. "
        "Em breve estarei pronto para ajudá-lo. Aguarde!"
    )

    # Salva mensagem de saída
    conversation_service.save_message(
        db,
        conversation=conversation,
        direction="outbound",
        content=response_text,
    )

    # Envia resposta via Z-API
    await zapi_service.send_text_message(payload.phone, response_text)

    return {"status": "processed"}
