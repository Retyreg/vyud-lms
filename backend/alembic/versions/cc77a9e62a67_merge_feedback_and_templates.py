"""merge_feedback_and_templates

Revision ID: cc77a9e62a67
Revises: a2b3c4d5e6f7, d5e6f7a8b9c0
Create Date: 2026-04-19 20:22:53.639125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc77a9e62a67'
down_revision: Union[str, Sequence[str], None] = ('a2b3c4d5e6f7', 'd5e6f7a8b9c0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
