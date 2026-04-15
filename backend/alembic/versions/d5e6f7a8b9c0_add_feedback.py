"""add feedback table

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_key', sa.String(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('liked', sa.Text(), nullable=True),
        sa.Column('missing', sa.Text(), nullable=True),
        sa.Column('feature', sa.Text(), nullable=True),
        sa.Column('contact', sa.String(), nullable=True),
        sa.Column('page', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('feedback')
