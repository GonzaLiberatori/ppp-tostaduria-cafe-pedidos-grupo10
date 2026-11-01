"""tueste en gramos, tipo de cafe y consumos

Revision ID: b7a1c9d4e2f0
Revises: 57cf7419baaf
Create Date: 2026-11-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7a1c9d4e2f0"
down_revision: Union[str, Sequence[str], None] = "57cf7419baaf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega el tipo de café a la orden y la trazabilidad de consumos."""
    with op.batch_alter_table("orden_tueste") as batch_op:
        batch_op.add_column(
            sa.Column("tipo_de_cafe_id", sa.Integer(), nullable=True)
        )
        batch_op.alter_column(
            "perfil_de_tostado_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.alter_column(
            "kg_gastados",
            existing_type=sa.Numeric(precision=10, scale=2),
            type_=sa.Numeric(precision=12, scale=3),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "kg_obtenidos",
            existing_type=sa.Numeric(precision=10, scale=2),
            type_=sa.Numeric(precision=12, scale=3),
            existing_nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_orden_tueste_tipo_de_cafe",
            "tipo_de_cafe",
            ["tipo_de_cafe_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_orden_tueste_tipo_de_cafe_id",
            ["tipo_de_cafe_id"],
            unique=False,
        )

    with op.batch_alter_table("lote") as batch_op:
        batch_op.alter_column(
            "kg_disponibles",
            existing_type=sa.Numeric(precision=10, scale=2),
            type_=sa.Numeric(precision=12, scale=3),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "kg_reales",
            existing_type=sa.Numeric(precision=10, scale=2),
            type_=sa.Numeric(precision=12, scale=3),
            existing_nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_lote_orden_tueste",
            "orden_tueste",
            ["orden_tueste_id"],
            ["id"],
        )

    op.create_table(
        "consumo_tueste",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("orden_tueste_id", sa.Integer(), nullable=False),
        sa.Column("lote_id", sa.Integer(), nullable=False),
        sa.Column(
            "kg_consumidos", sa.Numeric(precision=12, scale=3), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["orden_tueste_id"], ["orden_tueste.id"]
        ),
        sa.ForeignKeyConstraint(["lote_id"], ["lote.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_consumo_tueste_orden_tueste_id",
        "consumo_tueste",
        ["orden_tueste_id"],
        unique=False,
    )
    op.create_index(
        "ix_consumo_tueste_lote_id",
        "consumo_tueste",
        ["lote_id"],
        unique=False,
    )


def downgrade() -> None:
    """Revierte la trazabilidad y vuelve a los kilos con dos decimales."""
    op.drop_index(
        "ix_consumo_tueste_lote_id", table_name="consumo_tueste"
    )
    op.drop_index(
        "ix_consumo_tueste_orden_tueste_id", table_name="consumo_tueste"
    )
    op.drop_table("consumo_tueste")

    with op.batch_alter_table("lote") as batch_op:
        batch_op.drop_constraint(
            "fk_lote_orden_tueste", type_="foreignkey"
        )
        batch_op.alter_column(
            "kg_disponibles",
            existing_type=sa.Numeric(precision=12, scale=3),
            type_=sa.Numeric(precision=10, scale=2),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "kg_reales",
            existing_type=sa.Numeric(precision=12, scale=3),
            type_=sa.Numeric(precision=10, scale=2),
            existing_nullable=False,
        )

    with op.batch_alter_table("orden_tueste") as batch_op:
        batch_op.drop_index("ix_orden_tueste_tipo_de_cafe_id")
        batch_op.drop_constraint(
            "fk_orden_tueste_tipo_de_cafe", type_="foreignkey"
        )
        batch_op.alter_column(
            "kg_gastados",
            existing_type=sa.Numeric(precision=12, scale=3),
            type_=sa.Numeric(precision=10, scale=2),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "kg_obtenidos",
            existing_type=sa.Numeric(precision=12, scale=3),
            type_=sa.Numeric(precision=10, scale=2),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "perfil_de_tostado_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.drop_column("tipo_de_cafe_id")
