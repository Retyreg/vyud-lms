"""add_display_name_to_org_members

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-04-21 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'i3j4k5l6m7n8'
down_revision = 'h2i3j4k5l6m7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('org_members', sa.Column('display_name', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('org_members', 'display_name')
