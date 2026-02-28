"""Enable RLS on alembic_version

Revision ID: 013
Revises: 012
Create Date: 2026-02-28

Habilita Row Level Security (RLS) em alembic_version para resolver alerta do
Supabase. O role anon tem todos os privilégios por padrão e pode sobrescrever
o identificador de versão via PostgREST, o que poderia desorientar futuras
migrations.

Sem políticas explícitas → anon e authenticated completamente bloqueados.
O Alembic (postgres superusuário) contorna RLS automaticamente.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY;")
