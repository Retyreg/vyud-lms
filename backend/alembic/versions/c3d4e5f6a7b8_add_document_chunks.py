"""add document_chunks

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False, index=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),  # stored as text; pgvector handles casting
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
