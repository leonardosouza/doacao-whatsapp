import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message

logger = logging.getLogger(__name__)


def get_or_create_conversation(db: Session, phone_number: str) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.phone_number == phone_number,
            Conversation.status == "active",
        )
        .first()
    )

    if not conversation:
        conversation = Conversation(phone_number=phone_number)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        logger.info(f"Nova conversa criada para {phone_number}")

    return conversation


def save_message(
    db: Session,
    conversation: Conversation,
    direction: str,
    content: str,
    intent: str | None = None,
    sentiment: str | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation.id,
        direction=direction,
        content=content,
        intent=intent,
        sentiment=sentiment,
    )
    db.add(message)

    conversation.last_message_at = func.now()
    db.commit()
    db.refresh(message)

    return message
