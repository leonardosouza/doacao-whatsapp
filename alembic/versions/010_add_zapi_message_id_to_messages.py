"""add zapi_message_id to messages

Revision ID: 010
Revises: 009
Create Date: 2026-02-28

Adiciona coluna zapi_message_id (nullable, unique) à tabela messages para
deduplicação de webhooks reenviados pelo Z-API.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("zapi_message_id", sa.String(100), nullable=True),
    )
    op.create_index(
        "ix_messages_zapi_message_id",
        "messages",
        ["zapi_message_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_messages_zapi_message_id", table_name="messages")
    op.drop_column("messages", "zapi_message_id")
