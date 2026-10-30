"""Módulo de ventas: cobro, pagos y auditoría de anulaciones.

Solo crea tablas nuevas (``venta_comercial``, ``pago_venta`` y
``venta_comercial_historial``). No altera ninguna tabla existente, así que las
tablas heredadas ``venta`` y ``pago`` del módulo de pedidos quedan intactas.

Revision ID: 003_ventas
Revises: 57cf7419baaf
Create Date: 2026-10-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_ventas"
down_revision: Union[str, Sequence[str], None] = "57cf7419baaf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Los valores son los nombres de los miembros de los enums, igual que en las
# tablas que ya existen (``pago`` y ``venta``): SQLAlchemy persiste el nombre.
METODO_PAGO = sa.Enum(
    "EFECTIVO",
    "CREDITO",
    "DEBITO",
    "TRANSFERENCIA",
    "MERCADO_PAGO",
    "CHEQUE",
    "OTRO",
    name="metodopago",
)
MONEDA = sa.Enum("ARS", "USD", "EUR", "BRL", name="moneda")
FACTURACION = sa.Enum(
    "FACTURA_A",
    "CONSUMIDOR_FINAL",
    "TICKET",
    "NO_REQUIERE",
    name="facturacion",
)
VENTA_ESTADO = sa.Enum("CONFIRMADA", "ANULADA", name="ventaestado")


def upgrade() -> None:
    """Crea las tablas del módulo de ventas y sus índices."""
    op.create_table(
        "venta_comercial",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.Column("facturacion", FACTURACION, nullable=False),
        sa.Column("estado", VENTA_ESTADO, nullable=False),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("numero_comprobante", sa.String(length=20), nullable=True),
        sa.Column("cuenta_id", sa.Integer(), nullable=True),
        sa.Column("creada_en", sa.DateTime(), nullable=False),
        sa.Column("anulada_en", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedido.id"]),
        sa.ForeignKeyConstraint(["cuenta_id"], ["cuenta.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_venta_comercial_pedido_id", "venta_comercial", ["pedido_id"]
    )
    op.create_index(
        "ix_venta_comercial_numero_comprobante",
        "venta_comercial",
        ["numero_comprobante"],
        unique=True,
    )
    # Una sola venta vigente por pedido. El índice es parcial para permitir
    # volver a vender un pedido cuya venta anterior fue anulada.
    op.create_index(
        "ux_venta_comercial_pedido_vigente",
        "venta_comercial",
        ["pedido_id"],
        unique=True,
        sqlite_where=sa.text("estado = 'CONFIRMADA'"),
    )

    op.create_table(
        "pago_venta",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("venta_id", sa.Integer(), nullable=False),
        sa.Column("metodo_de_pago", METODO_PAGO, nullable=False),
        sa.Column("monto", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("moneda", MONEDA, nullable=False),
        sa.Column("aclaracion", sa.String(length=255), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["venta_id"], ["venta_comercial.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pago_venta_venta_id", "pago_venta", ["venta_id"])

    op.create_table(
        "venta_comercial_historial",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("venta_id", sa.Integer(), nullable=False),
        sa.Column("estado_anterior", VENTA_ESTADO, nullable=True),
        sa.Column("estado_nuevo", VENTA_ESTADO, nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=True),
        sa.Column("cuenta_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["venta_id"], ["venta_comercial.id"]),
        sa.ForeignKeyConstraint(["cuenta_id"], ["cuenta.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_venta_comercial_historial_venta_id",
        "venta_comercial_historial",
        ["venta_id"],
    )


def downgrade() -> None:
    """Elimina las tablas del módulo de ventas."""
    op.drop_index(
        "ix_venta_comercial_historial_venta_id",
        table_name="venta_comercial_historial",
    )
    op.drop_table("venta_comercial_historial")

    op.drop_index("ix_pago_venta_venta_id", table_name="pago_venta")
    op.drop_table("pago_venta")

    op.drop_index(
        "ux_venta_comercial_pedido_vigente", table_name="venta_comercial"
    )
    op.drop_index(
        "ix_venta_comercial_numero_comprobante", table_name="venta_comercial"
    )
    op.drop_index("ix_venta_comercial_pedido_id", table_name="venta_comercial")
    op.drop_table("venta_comercial")
