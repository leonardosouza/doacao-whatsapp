"""truncate conversations and messages for MVP clean start

Revision ID: 004
Revises: 003
Create Date: 2026-02-28

Esta é uma migration de dados (não altera schema).
Remove todos os registros de messages e conversations,
preservando ONGs, schema e sequência de versões do Alembic.

downgrade: não-operacional — dados deletados não podem ser recuperados.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # messages primeiro (FK aponta para conversations)
    op.execute("DELETE FROM messages")
    op.execute("DELETE FROM conversations")


def downgrade() -> None:
    # Dados deletados são irrecuperáveis — downgrade é intencional no-op.
    pass
