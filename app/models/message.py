import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        # Cobre 4 queries de alta frequência: get_conversation_history,
        # última msg do bot (profile_node), count_recent_inbound (rate-limit)
        # e has_consecutive_out_of_scope. PostgreSQL não indexa FK automaticamente.
        Index(
            "ix_messages_conversation_direction_created",
            "conversation_id",
            "direction",
            text("created_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id")
    )
    direction: Mapped[str] = mapped_column(String(10))  # "inbound" ou "outbound"
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(30), nullable=True)
    zapi_message_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
