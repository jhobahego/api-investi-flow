"""add_deleted_at_to_projects

Revision ID: e91e6743c3c1
Revises: 3569f95678a2
Create Date: 2026-10-10

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e91e6743c3c1"
down_revision: Union[str, Sequence[str], None] = "3569f95678a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deleted_at column to projects for soft-delete (archiving)."""
    op.add_column(
        "projects",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_projects_deleted_at"), "projects", ["deleted_at"], unique=False
    )


def downgrade() -> None:
    """Remove deleted_at column from projects."""
    op.drop_index(op.f("ix_projects_deleted_at"), table_name="projects")
    op.drop_column("projects", "deleted_at")
