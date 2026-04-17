"""merge heads

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8, d4e5f6a7b8c9
Create Date: 2026-04-01 21:45:00.000000

"""
from typing import Sequence, Union

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = ('c3d4e5f6a7b8', 'd4e5f6a7b8c9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
