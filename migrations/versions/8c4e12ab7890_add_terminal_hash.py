"""add terminal_hash to licenses

Revision ID: 8c4e12ab7890
Revises: 38e2d6a4a49d
Create Date: 2026-10-16 10:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c4e12ab7890'
down_revision: Union[str, None] = '38e2d6a4a49d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('licenses', sa.Column('terminal_hash', sa.String(length=100), nullable=True, server_default=''))


def downgrade() -> None:
    op.drop_column('licenses', 'terminal_hash')
