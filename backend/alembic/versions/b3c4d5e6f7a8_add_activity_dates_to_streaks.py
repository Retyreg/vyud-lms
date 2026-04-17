"""add activity_dates to user_streaks

Revision ID: b3c4d5e6f7a8
Revises: f1a2b3c4d5e6
Create Date: 2026-04-14

"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c4d5e6f7a8'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'user_streaks',
        sa.Column('activity_dates', sa.JSON(), nullable=False, server_default='[]'),
    )


def downgrade() -> None:
    op.drop_column('user_streaks', 'activity_dates')
