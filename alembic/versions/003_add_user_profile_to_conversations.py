"""add user_name and user_email to conversations

Revision ID: 003
Revises: 002
Create Date: 2026-02-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("user_name", sa.String(100), nullable=True))
    op.add_column("conversations", sa.Column("user_email", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "user_email")
    op.drop_column("conversations", "user_name")
