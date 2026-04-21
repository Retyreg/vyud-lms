"""add_demo_tables

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-04-21 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'g1h2i3j4k5l6'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'demo_users',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('company', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('industry', sa.String(), nullable=False),
        sa.Column('magic_token', sa.String(), nullable=False),
        sa.Column('session_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ai_calls_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_calls_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('demo_course_id', sa.Integer(), sa.ForeignKey('courses.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_demo_users_email', 'demo_users', ['email'], unique=True)
    op.create_index('ix_demo_users_magic_token', 'demo_users', ['magic_token'], unique=True)

    op.create_table(
        'demo_feedback',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('demo_user_id', UUID(as_uuid=False), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('message', sa.String(), nullable=True),
        sa.Column('wants_pilot', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['demo_user_id'], ['demo_users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_demo_feedback_demo_user_id', 'demo_feedback', ['demo_user_id'])


def downgrade() -> None:
    op.drop_table('demo_feedback')
    op.drop_index('ix_demo_users_magic_token', table_name='demo_users')
    op.drop_index('ix_demo_users_email', table_name='demo_users')
    op.drop_table('demo_users')
