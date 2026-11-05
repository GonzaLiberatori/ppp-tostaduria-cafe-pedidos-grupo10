"""tipo de lote en el detalle del pedido

Revision ID: 009_detalle_pedido_tipo_lote
Revises: 008_pedido_stock_restaurado
Create Date: 2026-11-04 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "009_detalle_pedido_tipo_lote"
down_revision: Union[str, Sequence[str], None] = "008_pedido_stock_restaurado"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Distingue si el ítem vendido es café verde o tostado.

    Los detalles existentes quedan como ``TOSTADO``: hasta ahora el panel solo
    vendía producto terminado y el stock se descontaba de esos lotes.
    """
    with op.batch_alter_table("detalle_pedido") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tipo_lote",
                sa.Enum(
                    "VERDE",
                    "TOSTADO",
                    name="detalle_pedido_tipo_lote_enum",
                ),
                nullable=False,
                server_default="TOSTADO",
            )
        )


def downgrade() -> None:
    """Quita el tipo de lote del detalle."""
    with op.batch_alter_table("detalle_pedido") as batch_op:
        batch_op.drop_column("tipo_lote")
