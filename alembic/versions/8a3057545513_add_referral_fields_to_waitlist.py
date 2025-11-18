"""add referral fields to waitlist

Revision ID: 8a3057545513
Revises: a82663bc85b7
Create Date: 2025-11-18 13:34:47.309406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a3057545513'
down_revision: Union[str, Sequence[str], None] = 'a82663bc85b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('waitlist', sa.Column('referral_code', sa.String(), nullable=True))
    op.add_column('waitlist', sa.Column('referred_by', sa.String(), nullable=True))
    op.add_column('waitlist', sa.Column('referral_count', sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('waitlist', 'referral_code')
    op.drop_column('waitlist', 'referred_by')
    op.drop_column('waitlist', 'referral_count')
