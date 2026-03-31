"""initial_schema

Revision ID: cc96d0acc729
Revises:
Create Date: 2026-03-08 23:11:00.128020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc96d0acc729'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', sa.Enum('student', 'curator', 'admin', name='userrole'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)

    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_courses_id', 'courses', ['id'], unique=False)
    op.create_index('ix_courses_title', 'courses', ['title'], unique=False)

    op.create_table(
        'lessons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_lessons_id', 'lessons', ['id'], unique=False)
    op.create_index('ix_lessons_title', 'lessons', ['title'], unique=False)

    op.create_table(
        'knowledge_nodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('prerequisites', sa.JSON(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('course_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id']),
        sa.ForeignKeyConstraint(['parent_id'], ['knowledge_nodes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_knowledge_nodes_id', 'knowledge_nodes', ['id'], unique=False)
    op.create_index('ix_knowledge_nodes_label', 'knowledge_nodes', ['label'], unique=False)

    op.create_table(
        'knowledge_edges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['knowledge_nodes.id']),
        sa.ForeignKeyConstraint(['target_id'], ['knowledge_nodes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_knowledge_edges_id', 'knowledge_edges', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_knowledge_edges_id', table_name='knowledge_edges')
    op.drop_table('knowledge_edges')

    op.drop_index('ix_knowledge_nodes_label', table_name='knowledge_nodes')
    op.drop_index('ix_knowledge_nodes_id', table_name='knowledge_nodes')
    op.drop_table('knowledge_nodes')

    op.drop_index('ix_lessons_title', table_name='lessons')
    op.drop_index('ix_lessons_id', table_name='lessons')
    op.drop_table('lessons')

    op.drop_index('ix_courses_title', table_name='courses')
    op.drop_index('ix_courses_id', table_name='courses')
    op.drop_table('courses')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')
    op.execute("DROP TYPE IF EXISTS userrole")
