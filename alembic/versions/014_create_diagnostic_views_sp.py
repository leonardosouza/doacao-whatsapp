"""Create diagnostic views with São Paulo timestamps

Revision ID: 014
Revises: 013
Create Date: 2026-02-28

Cria views diagnósticas que exibem timestamps em horário de São Paulo (UTC-3),
úteis para troubleshooting no Supabase dashboard e psql.

- v_messages_sp: mensagens com phone_number e created_at em horário SP
- v_conversations_sp: conversas com started_at e last_message_at em horário SP

Nenhum GRANT é concedido a anon/authenticated → acesso restrito ao superusuário.
O armazenamento continua em UTC (padrão correto); apenas a exibição muda.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE VIEW v_messages_sp AS
        SELECT
            m.id,
            c.phone_number,
            m.direction,
            m.content,
            m.intent,
            m.sentiment,
            m.zapi_message_id,
            (m.created_at AT TIME ZONE 'America/Sao_Paulo')::timestamp AS created_at_sp
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id;
    """)

    op.execute("""
        CREATE VIEW v_conversations_sp AS
        SELECT
            id,
            phone_number,
            status,
            user_name,
            (started_at AT TIME ZONE 'America/Sao_Paulo')::timestamp AS started_at_sp,
            (last_message_at AT TIME ZONE 'America/Sao_Paulo')::timestamp AS last_message_at_sp
        FROM conversations;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_messages_sp;")
    op.execute("DROP VIEW IF EXISTS v_conversations_sp;")
