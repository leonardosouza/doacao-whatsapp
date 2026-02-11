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


def get_conversation_history(
    db: Session,
    conversation: Conversation,
    limit: int = 10,
    exclude_message_id: str | None = None,
) -> list[Message]:
    """Recupera as últimas mensagens da conversa, excluindo opcionalmente uma mensagem por ID."""
    query = db.query(Message).filter(Message.conversation_id == conversation.id)
    if exclude_message_id:
        query = query.filter(Message.id != exclude_message_id)
    messages = query.order_by(Message.created_at.desc()).limit(limit).all()
    return list(reversed(messages))


def format_history(messages: list[Message]) -> str:
    """Formata mensagens em texto de histórico para os prompts."""
    if not messages:
        return ""
    lines = []
    for msg in messages:
        role = "Usuário" if msg.direction == "inbound" else "Assistente"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)
