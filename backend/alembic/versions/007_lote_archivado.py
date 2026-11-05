"""baja logica de lotes con historial

Revision ID: 007_lote_archivado
Revises: 006_tueste_gramos
Create Date: 2026-11-04 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007_lote_archivado"
down_revision: Union[str, Sequence[str], None] = "006_tueste_gramos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega la marca de baja lógica a los lotes.

    Los lotes con consumos de tueste no se pueden borrar físicamente sin perder
    la trazabilidad. En lugar de eso se archivan y dejan de listarse.
    """
    with op.batch_alter_table("lote") as batch_op:
        batch_op.add_column(
            sa.Column(
                "archivado",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    """Quita la marca de baja lógica."""
    with op.batch_alter_table("lote") as batch_op:
        batch_op.drop_column("archivado")
