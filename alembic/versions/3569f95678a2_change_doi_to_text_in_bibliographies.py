"""change_doi_to_text_in_bibliographies

Revision ID: 3569f95678a2
Revises: 0b60493739c7
Create Date: 2025-12-01 22:23:17.209069

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3569f95678a2"
down_revision: Union[str, Sequence[str], None] = "0b60493739c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change doi column from VARCHAR(255) to TEXT to support long URLs."""
    # Cambiar el tipo de columna de String(255) a Text
    op.alter_column(
        "bibliographies",
        "doi",
        type_=sa.Text(),
        existing_type=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert doi column from TEXT back to VARCHAR(255)."""
    # Revertir el cambio
    op.alter_column(
        "bibliographies",
        "doi",
        type_=sa.String(length=255),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
