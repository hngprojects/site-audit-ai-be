"""merge migration heads

Revision ID: 88409ed6529a
Revises: 4a468c70c14a, 7523d06a1fb7
Create Date: 2025-11-20 15:00:21.879522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88409ed6529a'
down_revision: Union[str, Sequence[str], None] = ('4a468c70c14a', '7523d06a1fb7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
