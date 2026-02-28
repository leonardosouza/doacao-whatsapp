"""drop donation_url from ongs

Revision ID: 007
Revises: 006
Create Date: 2026-02-28

Remove a coluna donation_url da tabela ongs.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("ongs", "donation_url")


def downgrade() -> None:
    op.add_column(
        "ongs",
        sa.Column("donation_url", sa.String(300), nullable=True),
    )
