"""Cobranza de ventas: venta a pagare con vencimiento.

Agrega ``fecha_vencimiento`` y ``cobrada_en`` a ``venta_comercial`` y amplia el
indice parcial de venta vigente para que una venta ``PENDIENTE_COBRO`` tambien
ocupe el lugar de la venta vigente del pedido.

El enum ``VentaEstado`` no necesita recrearse: en ``003_ventas`` se declaro sin
``create_constraint``, asi que SQLite guarda el nombre del miembro en un
``VARCHAR`` y no hay ``CHECK`` que ampliar.

Revision ID: 004_ventas_cobranza
Revises: 003_ventas
Create Date: 2026-11-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_ventas_cobranza"
down_revision: Union[str, Sequence[str], None] = "003_ventas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDICE_VIGENTE = "ux_venta_comercial_pedido_vigente"


def upgrade() -> None:
    """Agrega las columnas de cobranza y amplia el indice de venta vigente."""
    op.add_column(
        "venta_comercial",
        sa.Column("fecha_vencimiento", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "venta_comercial",
        sa.Column("cobrada_en", sa.DateTime(), nullable=True),
    )

    op.drop_index(INDICE_VIGENTE, table_name="venta_comercial")
    op.create_index(
        INDICE_VIGENTE,
        "venta_comercial",
        ["pedido_id"],
        unique=True,
        sqlite_where=sa.text("estado IN ('CONFIRMADA', 'PENDIENTE_COBRO')"),
    )


def downgrade() -> None:
    """Vuelve al esquema anterior sin dejar ventas pendientes sin fecha de cobro.

    Las filas ``PENDIENTE_COBRO`` se pasan a ``CONFIRMADA`` y se les asigna
    ``cobrada_en = fecha`` antes de borrar la columna: si no, quedarian ventas
    confirmadas sin fecha de cobro y el arqueo posterior las ignoraria.
    """
    op.execute(
        "UPDATE venta_comercial SET cobrada_en = fecha "
        "WHERE estado = 'PENDIENTE_COBRO' AND cobrada_en IS NULL"
    )
    op.execute(
        "UPDATE venta_comercial SET estado = 'CONFIRMADA' "
        "WHERE estado = 'PENDIENTE_COBRO'"
    )

    op.drop_index(INDICE_VIGENTE, table_name="venta_comercial")
    op.create_index(
        INDICE_VIGENTE,
        "venta_comercial",
        ["pedido_id"],
        unique=True,
        sqlite_where=sa.text("estado = 'CONFIRMADA'"),
    )

    op.drop_column("venta_comercial", "cobrada_en")
    op.drop_column("venta_comercial", "fecha_vencimiento")
