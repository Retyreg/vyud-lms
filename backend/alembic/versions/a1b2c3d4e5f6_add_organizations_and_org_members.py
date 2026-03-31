"""add_organizations_and_org_members

Revision ID: a1b2c3d4e5f6
Revises: cc96d0acc729
Create Date: 2026-03-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'cc96d0acc729'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('invite_code', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'], unique=False)
    op.create_index('ix_organizations_invite_code', 'organizations', ['invite_code'], unique=True)

    op.create_table(
        'org_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('user_key', sa.String(), nullable=False),
        sa.Column('is_manager', sa.Boolean(), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_org_members_id', 'org_members', ['id'], unique=False)
    op.create_index('ix_org_members_org_id', 'org_members', ['org_id'], unique=False)

    op.add_column('courses', sa.Column('org_id', sa.Integer(), nullable=True))
    op.create_index('ix_courses_org_id', 'courses', ['org_id'], unique=False)
    op.create_foreign_key('fk_courses_org_id', 'courses', 'organizations', ['org_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_courses_org_id', 'courses', type_='foreignkey')
    op.drop_index('ix_courses_org_id', table_name='courses')
    op.drop_column('courses', 'org_id')

    op.drop_index('ix_org_members_org_id', table_name='org_members')
    op.drop_index('ix_org_members_id', table_name='org_members')
    op.drop_table('org_members')

    op.drop_index('ix_organizations_invite_code', table_name='organizations')
    op.drop_index('ix_organizations_id', table_name='organizations')
    op.drop_table('organizations')
