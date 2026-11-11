"""add message sources and attachment indexing status

Revision ID: 7c1d9e4a2b6f
Revises: f3a9c1d7b2e4
Create Date: 2026-11-10

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c1d9e4a2b6f"
down_revision: Union[str, Sequence[str], None] = "f3a9c1d7b2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add message sources and attachment indexing status."""
    op.add_column("messages", sa.Column("sources", sa.JSON(), nullable=True))

    with op.batch_alter_table("attachments") as batch_op:
        batch_op.add_column(
            sa.Column(
                "indexing_status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.create_check_constraint(
            "ck_attachments_indexing_status",
            "indexing_status IN ('pending','indexing','indexed','error')",
        )

    op.execute(
        "UPDATE attachments SET indexing_status='indexed' "
        "WHERE id IN (SELECT DISTINCT attachment_id FROM document_chunks)"
    )


def downgrade() -> None:
    """Drop attachment indexing status and message sources."""
    with op.batch_alter_table("attachments") as batch_op:
        batch_op.drop_constraint("ck_attachments_indexing_status", type_="check")
        batch_op.drop_column("indexing_status")

    op.drop_column("messages", "sources")
