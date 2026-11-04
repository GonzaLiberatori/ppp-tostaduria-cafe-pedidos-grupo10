"""Envíos programados: suscripciones B2B y entregas diarias.

Crea las dos tablas del módulo:

- ``suscripcion_envio``: configuración comercial recurrente por cliente.
- ``entrega_programada``: ocurrencia concreta de un día, con la restricción
  ``UNIQUE (cliente_id, fecha_entrega)`` que respalda la idempotencia del job.

El enum ``EstadoEntrega`` se declara sin ``create_constraint`` (igual que el
resto de los enums del proyecto), así que SQLite guarda el nombre del miembro en
un ``VARCHAR`` y no hace falta recrear ningún ``CHECK``.

Revision ID: 005_envios_programados
Revises: 004_ventas_cobranza
Create Date: 2026-11-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005_envios_programados"
down_revision: Union[str, Sequence[str], None] = "004_ventas_cobranza"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ESTADO_ENTREGA = sa.Enum(
    "PROGRAMADA",
    "GENERADA",
    "ERROR",
    "CANCELADA",
    name="estadoentrega",
)


def upgrade() -> None:
    """Crea las tablas de suscripciones y entregas programadas."""
    op.create_table(
        "suscripcion_envio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("tipo_de_cafe_id", sa.Integer(), nullable=True),
        sa.Column("blend_id", sa.Integer(), nullable=True),
        sa.Column(
            "cantidad_kg", sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("plazo_dias", sa.Integer(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("creada_en", sa.DateTime(), nullable=False),
        sa.Column("actualizada_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.persona_id"]),
        sa.ForeignKeyConstraint(["tipo_de_cafe_id"], ["tipo_de_cafe.id"]),
        sa.ForeignKeyConstraint(["blend_id"], ["blend.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_suscripcion_envio_cliente_id",
        "suscripcion_envio",
        ["cliente_id"],
    )

    op.create_table(
        "entrega_programada",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("fecha_entrega", sa.Date(), nullable=False),
        sa.Column(
            "estado", ESTADO_ENTREGA, nullable=False, server_default="PROGRAMADA"
        ),
        sa.Column("pedido_id", sa.Integer(), nullable=True),
        sa.Column("suscripcion_id", sa.Integer(), nullable=True),
        sa.Column("generada_en", sa.DateTime(), nullable=True),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.Column("creada_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.persona_id"]),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedido.id"]),
        sa.ForeignKeyConstraint(
            ["suscripcion_id"], ["suscripcion_envio.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cliente_id",
            "fecha_entrega",
            name="uq_entrega_programada_cliente_fecha",
        ),
    )
    op.create_index(
        "ix_entrega_programada_cliente_id",
        "entrega_programada",
        ["cliente_id"],
    )
    op.create_index(
        "ix_entrega_programada_fecha_entrega",
        "entrega_programada",
        ["fecha_entrega"],
    )

    # Corrige el ancho heredado de 003: al agregarse ``PENDIENTE_COBRO`` el
    # mayor miembro de ``VentaEstado`` mide 15 caracteres, pero la columna quedó
    # en ``VARCHAR(10)``. SQLite ignora el largo, aunque ``alembic check`` lo
    # reporta como drift y otro motor truncaría el valor.
    with op.batch_alter_table("venta_comercial") as batch:
        batch.alter_column(
            "estado",
            type_=sa.String(length=15),
            existing_nullable=False,
        )
    with op.batch_alter_table("venta_comercial_historial") as batch:
        batch.alter_column(
            "estado_anterior",
            type_=sa.String(length=15),
            existing_nullable=True,
        )
        batch.alter_column(
            "estado_nuevo",
            type_=sa.String(length=15),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Elimina las tablas de envíos programados."""
    op.drop_index(
        "ix_entrega_programada_fecha_entrega",
        table_name="entrega_programada",
    )
    op.drop_index(
        "ix_entrega_programada_cliente_id",
        table_name="entrega_programada",
    )
    op.drop_table("entrega_programada")

    op.drop_index(
        "ix_suscripcion_envio_cliente_id",
        table_name="suscripcion_envio",
    )
    op.drop_table("suscripcion_envio")
