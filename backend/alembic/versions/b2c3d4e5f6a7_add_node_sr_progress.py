"""add_node_sr_progress

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'node_sr_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.Column('user_key', sa.String(), nullable=False),
        sa.Column('easiness_factor', sa.Float(), nullable=False, server_default='2.5'),
        sa.Column('interval', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('repetitions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_review', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_reviewed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_reviews', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_reviews', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['node_id'], ['knowledge_nodes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_node_sr_progress_id', 'node_sr_progress', ['id'], unique=False)
    op.create_index('ix_node_sr_progress_node_id', 'node_sr_progress', ['node_id'], unique=False)
    op.create_index('ix_node_sr_progress_user_key', 'node_sr_progress', ['user_key'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_node_sr_progress_user_key', table_name='node_sr_progress')
    op.drop_index('ix_node_sr_progress_node_id', table_name='node_sr_progress')
    op.drop_index('ix_node_sr_progress_id', table_name='node_sr_progress')
    op.drop_table('node_sr_progress')
