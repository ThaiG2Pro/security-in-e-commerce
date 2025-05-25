"""add expires_at to reset_tokens table

Revision ID: a1b2c3d4e5f6
Revises: 1a2b3c4d5e6f
Create Date: 2025-05-25 12:57:08.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('ALTER TABLE reset_tokens ADD COLUMN expires_at TIMESTAMP')
    op.execute('UPDATE reset_tokens SET expires_at = CURRENT_TIMESTAMP + INTERVAL \'24 hours\'')


def downgrade() -> None:
    op.execute('ALTER TABLE reset_tokens DROP COLUMN expires_at')
