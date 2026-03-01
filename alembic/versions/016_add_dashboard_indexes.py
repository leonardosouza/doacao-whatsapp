"""Add performance indexes for dashboard analytical queries

Revision ID: 016
Revises: 015
Create Date: 2026-02-28

O dashboard (doazap-dashboard) executa queries analíticas com padrões distintos
das queries do bot: varreduras por intervalo de data e agrupamentos por intent.
Os índices da migration 015 foram projetados para o bot (filtros por conversation_id)
e são inúteis para queries sem esse prefixo.

Índices adicionados:

1. ix_messages_created_at
   B-tree em messages(created_at DESC).
   Cobre queries que filtram só por data, sem direction:
   - kpi_messages_today()    → WHERE created_at >= CURRENT_DATE
   - volume_by_hour_24h()    → WHERE created_at >= NOW() - INTERVAL '24 hours'

2. ix_messages_outbound_intent_created (partial)
   Parcial em messages(created_at DESC) WHERE direction = 'outbound' AND intent IS NOT NULL.
   Cobre 5 queries de analytics de intent e guard-rails:
   - kpi_top_intent_today()    → direction='outbound' AND intent IS NOT NULL AND created_at >= hoje
   - intent_distribution()     → direction='outbound' AND intent IS NOT NULL AND created_at >= N dias
   - intent_evolution_weekly() → direction='outbound' AND intent IS NOT NULL (todos os períodos)
   - sentiment_by_intent()     → direction='outbound' AND intent IS NOT NULL AND sentiment IS NOT NULL
   - oos_rate_daily()          → direction='outbound' AND intent IS NOT NULL AND created_at >= N dias
   Por ser parcial (~50% do volume total de mensagens), o índice é compacto e seletivo.

3. ix_conversations_started_at
   B-tree em conversations(started_at DESC).
   Cobre queries de KPI e gráficos de conversas por data:
   - kpi_conversations_today()  → WHERE started_at >= CURRENT_DATE
   - kpi_unique_users_today()   → WHERE started_at >= CURRENT_DATE
   - conversations_per_day()    → WHERE started_at >= NOW() - INTERVAL ':days days'
   - guardrail_events_summary() → GROUP BY DATE(started_at) ORDER BY dia DESC LIMIT 30

4. ix_conversations_last_message_at
   B-tree em conversations(last_message_at DESC).
   Cobre recent_conversations() que ordena por last_message_at DESC LIMIT 10.
   Com índice, o PostgreSQL faz index scan com early stop em vez de sort completo.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. messages.created_at — cobre queries de data sem filtro por conversation_id
    op.create_index(
        "ix_messages_created_at",
        "messages",
        [sa.text("created_at DESC")],
    )

    # 2. Partial index para queries de intent/guard-rails (outbound + intent preenchido)
    op.create_index(
        "ix_messages_outbound_intent_created",
        "messages",
        [sa.text("created_at DESC")],
        postgresql_where=sa.text("direction = 'outbound' AND intent IS NOT NULL"),
    )

    # 3. conversations.started_at — KPI de hoje vs ontem e gráficos por período
    op.create_index(
        "ix_conversations_started_at",
        "conversations",
        [sa.text("started_at DESC")],
    )

    # 4. conversations.last_message_at — ORDER BY + LIMIT em recent_conversations()
    op.create_index(
        "ix_conversations_last_message_at",
        "conversations",
        [sa.text("last_message_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_last_message_at", table_name="conversations")
    op.drop_index("ix_conversations_started_at", table_name="conversations")
    op.drop_index("ix_messages_outbound_intent_created", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")
