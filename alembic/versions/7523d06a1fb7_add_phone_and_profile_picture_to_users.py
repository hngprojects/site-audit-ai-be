"""add_phone_and_profile_picture_to_users

Revision ID: 7523d06a1fb7
Revises: 4a74745ccc78
Create Date: 2025-11-20 12:59:13.053889

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7523d06a1fb7'
down_revision: Union[str, Sequence[str], None] = '6888d4c4a86d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('phone_number', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('profile_picture_url', sa.String(500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'profile_picture_url')
    op.drop_column('users', 'phone_number')
