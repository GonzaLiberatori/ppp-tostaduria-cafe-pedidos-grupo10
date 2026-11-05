"""marca de stock restaurado en pedidos

Revision ID: 008_pedido_stock_restaurado
Revises: 007_lote_archivado
Create Date: 2026-11-04 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "008_pedido_stock_restaurado"
down_revision: Union[str, Sequence[str], None] = "007_lote_archivado"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Marca si el stock de cada pedido está devuelto al inventario.

    Los pedidos existentes quedan en ``False``: su stock se descontó al
    crearse y todavía no fue devuelto. Así una venta nueva sobre un pedido
    viejo no lo descuenta dos veces.
    """
    with op.batch_alter_table("pedido") as batch_op:
        batch_op.add_column(
            sa.Column(
                "stock_restaurado",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    """Quita la marca de stock restaurado."""
    with op.batch_alter_table("pedido") as batch_op:
        batch_op.drop_column("stock_restaurado")
