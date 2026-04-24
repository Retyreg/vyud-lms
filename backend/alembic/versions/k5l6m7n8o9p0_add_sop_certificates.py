"""add_sop_certificates

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-04-23 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'k5l6m7n8o9p0'
down_revision = 'j4k5l6m7n8o9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sop_certificates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_key', sa.String(), nullable=False),
        sa.Column('sop_id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('cert_token', sa.String(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('max_score', sa.Integer(), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['sop_id'], ['sops.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cert_token'),
    )
    op.create_index('ix_sop_certificates_user_key', 'sop_certificates', ['user_key'])
    op.create_index('ix_sop_certificates_sop_id', 'sop_certificates', ['sop_id'])


def downgrade() -> None:
    op.drop_index('ix_sop_certificates_sop_id', 'sop_certificates')
    op.drop_index('ix_sop_certificates_user_key', 'sop_certificates')
    op.drop_table('sop_certificates')
