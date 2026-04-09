"""add_sops_sop_steps_sop_completions

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-04-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sops',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('quiz_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sops_id'), 'sops', ['id'], unique=False)
    op.create_index(op.f('ix_sops_org_id'), 'sops', ['org_id'], unique=False)

    op.create_table(
        'sop_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sop_id', sa.Integer(), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['sop_id'], ['sops.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sop_steps_id'), 'sop_steps', ['id'], unique=False)
    op.create_index(op.f('ix_sop_steps_sop_id'), 'sop_steps', ['sop_id'], unique=False)

    op.create_table(
        'sop_completions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sop_id', sa.Integer(), nullable=False),
        sa.Column('user_key', sa.String(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('max_score', sa.Integer(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('time_spent_sec', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['sop_id'], ['sops.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sop_completions_id'), 'sop_completions', ['id'], unique=False)
    op.create_index(op.f('ix_sop_completions_sop_id'), 'sop_completions', ['sop_id'], unique=False)
    op.create_index(op.f('ix_sop_completions_user_key'), 'sop_completions', ['user_key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sop_completions_user_key'), table_name='sop_completions')
    op.drop_index(op.f('ix_sop_completions_sop_id'), table_name='sop_completions')
    op.drop_index(op.f('ix_sop_completions_id'), table_name='sop_completions')
    op.drop_table('sop_completions')

    op.drop_index(op.f('ix_sop_steps_sop_id'), table_name='sop_steps')
    op.drop_index(op.f('ix_sop_steps_id'), table_name='sop_steps')
    op.drop_table('sop_steps')

    op.drop_index(op.f('ix_sops_org_id'), table_name='sops')
    op.drop_index(op.f('ix_sops_id'), table_name='sops')
    op.drop_table('sops')
