"""Crear tablas de usuarios, refresh tokens y clientes.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "rol",
            sa.Enum(
                "ADMIN",
                "EMPLEADO",
                "VENDEDOR",
                name="rol_usuario",
            ),
            nullable=False,
        ),
        sa.Column(
            "activo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_usuarios_username"),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_usuarios_username", "usuarios", ["username"])

    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum("B2B", "B2C", name="tipo_cliente"),
            nullable=False,
            server_default=sa.text("'B2C'"),
        ),
        sa.Column(
            "kilos_comprados",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "deuda_pendiente",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("telefono", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("direccion", sa.String(length=255), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "kilos_comprados >= 0",
            name="ck_clientes_kilos_no_negativos",
        ),
        # deuda_pendiente admite negativos (saldo a favor del cliente).
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expira_en", sa.DateTime(), nullable=False),
        sa.Column("revocado_en", sa.DateTime(), nullable=True),
        sa.Column("reemplazado_por", sa.String(length=64), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name="fk_refresh_tokens_usuario",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_refresh_tokens_token_hash",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_refresh_tokens_usuario_id",
        "refresh_tokens",
        ["usuario_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_refresh_tokens_usuario_id",
        table_name="refresh_tokens",
    )
    op.drop_table("refresh_tokens")
    op.drop_table("clientes")
    op.drop_index("ix_usuarios_username", table_name="usuarios")
    op.drop_table("usuarios")
