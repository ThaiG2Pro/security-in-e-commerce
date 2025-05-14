"""add role column to users table

Revision ID: 1a2b3c4d5e6f
Revises: e8c9ea267498
Create Date: 2025-05-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, None] = 'e8c9ea267498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('users', sa.Column('role', sa.Text(), nullable=False, server_default='user'))
    op.execute("UPDATE users SET role='user' WHERE role IS NULL")
    op.alter_column('users', 'role', server_default=None)

def downgrade() -> None:
    op.drop_column('users', 'role')
