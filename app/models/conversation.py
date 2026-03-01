import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        # Índice parcial — cobre get_or_create_conversation() que sempre filtra
        # por phone_number AND status = 'active'. Mais seletivo que índice composto.
        Index(
            "ix_conversations_phone_active",
            "phone_number",
            postgresql_where=text("status = 'active'"),
        ),
        # Cobre queries de KPI e gráficos por data:
        # kpi_conversations_today, kpi_unique_users_today, conversations_per_day,
        # guardrail_events_summary
        Index(
            "ix_conversations_started_at",
            text("started_at DESC"),
        ),
        # Cobre recent_conversations() ORDER BY last_message_at DESC LIMIT 10
        # — index scan com early stop em vez de sort completo
        Index(
            "ix_conversations_last_message_at",
            text("last_message_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")
