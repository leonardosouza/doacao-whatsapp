"""Enable RLS on public tables

Revision ID: 012
Revises: 011
Create Date: 2026-02-28

Habilita Row Level Security (RLS) nas tabelas expostas via PostgREST do Supabase.
O role anon tem todos os privilégios por padrão no Supabase e, sem RLS, pode
ler/modificar dados sensíveis (telefones, conversas) diretamente via PostgREST
sem passar pelo FastAPI.

Políticas implementadas:
- ongs: SELECT público para anon (dado público, consistente com GET /api/ongs)
        INSERT/UPDATE/DELETE bloqueados para anon (requerem API Key no FastAPI)
- conversations: sem política → anon completamente bloqueado (dado sensível: telefone)
- messages: sem política → anon completamente bloqueado (dado sensível: conversas)

O app FastAPI conecta como postgres (superusuário) e contorna o RLS automaticamente.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Habilita RLS nas três tabelas da aplicação
    op.execute("ALTER TABLE public.ongs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;")

    # ongs: leitura pública para anon (dado público, consistente com GET /api/ongs sem auth)
    # escritas (INSERT/UPDATE/DELETE) sem política → bloqueadas para anon por RLS
    op.execute("""
        CREATE POLICY "anon_select_ongs"
        ON public.ongs
        FOR SELECT
        TO anon
        USING (true);
    """)
    # conversations e messages: sem políticas para anon → todos os acessos bloqueados


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "anon_select_ongs" ON public.ongs;')
    op.execute("ALTER TABLE public.ongs DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.conversations DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.messages DISABLE ROW LEVEL SECURITY;")
