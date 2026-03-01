"""Add performance indexes for high-frequency queries

Revision ID: 015
Revises: 014
Create Date: 2026-02-28

Adiciona dois índices para otimizar as consultas mais frequentes do sistema:

1. ix_messages_conversation_direction_created
   Índice composto em messages(conversation_id, direction, created_at DESC).
   PostgreSQL NÃO cria índice automaticamente em colunas FK — esta ausência afeta
   4 queries críticas executadas em toda mensagem recebida:
   - get_conversation_history()             → WHERE conversation_id = :id ORDER BY created_at
   - profile_node (última msg do bot)       → WHERE conversation_id = :id AND direction = 'outbound' ORDER BY created_at DESC LIMIT 1
   - count_recent_inbound() (rate-limit)    → WHERE conversation_id = :id AND direction = 'inbound' AND created_at >= :cutoff
   - has_consecutive_out_of_scope()         → WHERE conversation_id = :id AND direction = 'outbound' ORDER BY created_at DESC LIMIT N
   O prefixo (conversation_id) cobre as queries de igualdade; a ordem DESC em
   created_at elimina sort reverso para as queries com ORDER BY created_at DESC.

2. ix_conversations_phone_active (partial index)
   Índice parcial em conversations(phone_number) WHERE status = 'active'.
   get_or_create_conversation() sempre filtra por phone_number AND status = 'active'.
   Um índice parcial é menor e mais seletivo que um índice composto completo.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Índice composto em messages — cobre 4 queries de alta frequência
    op.create_index(
        "ix_messages_conversation_direction_created",
        "messages",
        ["conversation_id", "direction", sa.text("created_at DESC")],
    )

    # 2. Índice parcial em conversations — somente conversas ativas
    op.create_index(
        "ix_conversations_phone_active",
        "conversations",
        ["phone_number"],
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_phone_active", table_name="conversations")
    op.drop_index(
        "ix_messages_conversation_direction_created", table_name="messages"
    )
