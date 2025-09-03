"""add_user_profile_fields

Revision ID: 1fb22cb55114
Revises: 405c840bd389
Create Date: 2025-08-14 22:16:43.560046

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1fb22cb55114"
down_revision: Union[str, Sequence[str], None] = "405c840bd389"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Agregar phone_number como nullable para compatibilidad con datos existentes
    # En producción, se debería requerir que los usuarios actualicen su perfil
    op.add_column("users", sa.Column("phone_number", sa.String(), nullable=True))
    op.add_column("users", sa.Column("university", sa.String(), nullable=True))
    op.add_column("users", sa.Column("research_group", sa.String(), nullable=True))
    op.add_column("users", sa.Column("career", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar los campos agregados
    op.drop_column("users", "career")
    op.drop_column("users", "research_group")
    op.drop_column("users", "university")
    op.drop_column("users", "phone_number")
