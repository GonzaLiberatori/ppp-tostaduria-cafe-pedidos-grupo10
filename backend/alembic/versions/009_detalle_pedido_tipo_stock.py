"""tipo de stock en el detalle del pedido

Revision ID: 009_detalle_pedido_tipo_stock
Revises: 008_pedido_stock_restaurado
Create Date: 2026-11-04 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "009_detalle_pedido_tipo_stock"
down_revision: Union[str, Sequence[str], None] = "008_pedido_stock_restaurado"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Distingue los ítems vendidos como café verde o tostado.

    Los pedidos existentes se completan con ``TOSTADO``: hasta esta versión
    solo se podía vender café tostado.
    """
    with op.batch_alter_table("detalle_pedido") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tipo_stock",
                sa.Enum(
                    "VERDE",
                    "TOSTADO",
                    name="detalle_pedido_tipo_stock",
                    native_enum=False,
                ),
                nullable=False,
                server_default="TOSTADO",
            )
        )


def downgrade() -> None:
    """Quita el tipo de stock del detalle."""
    with op.batch_alter_table("detalle_pedido") as batch_op:
        batch_op.drop_column("tipo_stock")
