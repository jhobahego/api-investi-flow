"""add document_chunks with pgvector embedding

Revision ID: f3a9c1d7b2e4
Revises: e91e6743c3c1
Create Date: 2026-11-08

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a9c1d7b2e4"
down_revision: Union[str, Sequence[str], None] = "e91e6743c3c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create document_chunks with a native vector column on PostgreSQL.

    SQLite (used by the test suite) has no ``vector`` type, so the embedding
    column falls back to TEXT and the index is a plain B-tree index.
    """
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        from pgvector.sqlalchemy import Vector

        embedding_type: sa.types.TypeEngine = Vector(768)
    else:
        embedding_type = sa.Text()

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attachment_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attachment_id"], ["attachments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attachment_id",
            "chunk_index",
            name="uq_document_chunks_attachment_chunk",
        ),
    )

    op.create_index(
        op.f("ix_document_chunks_id"), "document_chunks", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_document_chunks_attachment_id"),
        "document_chunks",
        ["attachment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_chunks_project_id"),
        "document_chunks",
        ["project_id"],
        unique=False,
    )

    if is_postgres:
        op.create_index(
            "ix_document_chunks_embedding_hnsw",
            "document_chunks",
            ["embedding"],
            unique=False,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )
    else:
        op.create_index(
            "ix_document_chunks_embedding_hnsw",
            "document_chunks",
            ["embedding"],
            unique=False,
        )


def downgrade() -> None:
    """Drop indexes and table. The vector extension is intentionally kept."""
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_project_id"), table_name="document_chunks")
    op.drop_index(
        op.f("ix_document_chunks_attachment_id"), table_name="document_chunks"
    )
    op.drop_index(op.f("ix_document_chunks_id"), table_name="document_chunks")
    op.drop_table("document_chunks")
