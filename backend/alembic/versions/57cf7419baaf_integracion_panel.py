"""Integración del panel: fecha de alta, código y fecha de lote, contacto y
autoservicio de clientes.

Revision ID: 57cf7419baaf
Revises: 8e15bc96d2aa
Create Date: 2026-10-29 12:59:18.046063

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57cf7419baaf'
down_revision: Union[str, Sequence[str], None] = '8e15bc96d2aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega las columnas y relaja las restricciones que pide el panel."""
    with op.batch_alter_table('cliente', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fecha_alta', sa.DateTime(), nullable=True))

    with op.batch_alter_table('lote', schema=None) as batch_op:
        batch_op.add_column(sa.Column('codigo_lote', sa.String(length=50), nullable=True))
        batch_op.add_column(
            sa.Column(
                'fecha_ingreso',
                sa.DateTime(),
                server_default=sa.text('(CURRENT_TIMESTAMP)'),
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f('ix_lote_codigo_lote'), ['codigo_lote'], unique=False
        )

    with op.batch_alter_table('pedido', schema=None) as batch_op:
        batch_op.alter_column(
            'empleado_persona_id',
            existing_type=sa.INTEGER(),
            nullable=True,
        )

    with op.batch_alter_table('persona', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=100), nullable=True))
        batch_op.alter_column(
            'telefono',
            existing_type=sa.VARCHAR(length=25),
            nullable=True,
        )
        batch_op.create_unique_constraint('uq_persona_email', ['email'])


def downgrade() -> None:
    """Revierte los cambios, salvo que los datos impidan volver atrás."""
    with op.batch_alter_table('persona', schema=None) as batch_op:
        batch_op.drop_constraint('uq_persona_email', type_='unique')
        batch_op.alter_column(
            'telefono',
            existing_type=sa.VARCHAR(length=25),
            nullable=False,
        )
        batch_op.drop_column('email')

    with op.batch_alter_table('pedido', schema=None) as batch_op:
        batch_op.alter_column(
            'empleado_persona_id',
            existing_type=sa.INTEGER(),
            nullable=False,
        )

    with op.batch_alter_table('lote', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_lote_codigo_lote'))
        batch_op.drop_column('fecha_ingreso')
        batch_op.drop_column('codigo_lote')

    with op.batch_alter_table('cliente', schema=None) as batch_op:
        batch_op.drop_column('fecha_alta')
