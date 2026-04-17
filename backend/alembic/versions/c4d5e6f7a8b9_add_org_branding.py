"""add org branding fields

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-04-14

"""
from alembic import op
import sqlalchemy as sa

revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('organizations', sa.Column('brand_color', sa.String(), nullable=True))
    op.add_column('organizations', sa.Column('logo_url', sa.String(), nullable=True))
    op.add_column('organizations', sa.Column('bot_username', sa.String(), nullable=True))
    op.add_column('organizations', sa.Column('display_name', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('organizations', 'display_name')
    op.drop_column('organizations', 'bot_username')
    op.drop_column('organizations', 'logo_url')
    op.drop_column('organizations', 'brand_color')
