"""delete stress test ONGs (email ILIKE '%stress%')

Revision ID: 005
Revises: 004
Create Date: 2026-02-28

Remove os 53 registros de ONGs criados pelos testes de carga (Locust).
Padrão identificado: email no formato stress-<hex>@test.local e
nomes "ONG Stress Test *" / "ONG Atualizada *".

downgrade: não-operacional — dados deletados não podem ser recuperados.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM ongs WHERE email ILIKE '%stress%'")


def downgrade() -> None:
    # Dados deletados são irrecuperáveis — downgrade é intencional no-op.
    pass
