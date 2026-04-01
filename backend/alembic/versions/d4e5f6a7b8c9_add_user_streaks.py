"""add_user_streaks

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_streaks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_key', sa.String(), nullable=False),
        sa.Column('current_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('longest_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_activity_date', sa.Date(), nullable=True),
        sa.Column('total_days_active', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_key'),
    )
    op.create_index('ix_user_streaks_id', 'user_streaks', ['id'], unique=False)
    op.create_index('ix_user_streaks_user_key', 'user_streaks', ['user_key'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_user_streaks_user_key', table_name='user_streaks')
    op.drop_index('ix_user_streaks_id', table_name='user_streaks')
    op.drop_table('user_streaks')
