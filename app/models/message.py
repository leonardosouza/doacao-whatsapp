import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        # Cobre 4 queries de alta frequência do bot: get_conversation_history,
        # última msg do bot (profile_node), count_recent_inbound (rate-limit)
        # e has_consecutive_out_of_scope. PostgreSQL não indexa FK automaticamente.
        Index(
            "ix_messages_conversation_direction_created",
            "conversation_id",
            "direction",
            text("created_at DESC"),
        ),
        # Cobre queries do dashboard sem filtro por conversation_id:
        # kpi_messages_today() e volume_by_hour_24h()
        Index(
            "ix_messages_created_at",
            text("created_at DESC"),
        ),
        # Índice parcial (~50% do volume) para queries de intents e guard-rails:
        # kpi_top_intent_today, intent_distribution, intent_evolution_weekly,
        # sentiment_by_intent, oos_rate_daily
        Index(
            "ix_messages_outbound_intent_created",
            text("created_at DESC"),
            postgresql_where=text("direction = 'outbound' AND intent IS NOT NULL"),
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
