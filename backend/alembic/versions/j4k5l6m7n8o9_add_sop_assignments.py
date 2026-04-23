"""add_sop_assignments

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-04-23 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'j4k5l6m7n8o9'
down_revision = 'i3j4k5l6m7n8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sop_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('sop_id', sa.Integer(), nullable=False),
        sa.Column('user_key', sa.String(), nullable=False),
        sa.Column('assigned_by', sa.String(), nullable=False),
        sa.Column('deadline', sa.Date(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('reminder_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['sop_id'], ['sops.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sop_assignments_org_id', 'sop_assignments', ['org_id'])
    op.create_index('ix_sop_assignments_user_key', 'sop_assignments', ['user_key'])
    op.create_index('ix_sop_assignments_sop_id', 'sop_assignments', ['sop_id'])


def downgrade() -> None:
    op.drop_index('ix_sop_assignments_sop_id', 'sop_assignments')
    op.drop_index('ix_sop_assignments_user_key', 'sop_assignments')
    op.drop_index('ix_sop_assignments_org_id', 'sop_assignments')
    op.drop_table('sop_assignments')
