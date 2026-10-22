"""create pedidos tables

Revision ID: 001_create_pedidos_tables
Revises: 
Create Date: 2026-10-21 20:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '001_create_pedidos_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for estado_pedido
    op.execute("CREATE TYPE estado_pedido_enum AS ENUM ('Pendiente', 'Listo', 'Entregado')")

    # Create pedidos table
    op.create_table(
        'pedidos',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('cliente_id', sa.BigInteger(), nullable=False),
        sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('estado', sa.Enum('Pendiente', 'Listo', 'Entregado', name='estado_pedido_enum', create_constraint=True, validate_strings=True, native_enum=False), nullable=False, server_default='Pendiente'),
        sa.Column('medio_contacto', sa.String(50), nullable=False, server_default='WhatsApp'),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('total', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('idempotency_key', sa.String(64), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
    )
    op.create_index('ix_pedidos_cliente_fecha', 'pedidos', ['cliente_id', 'fecha'], unique=False)
    op.create_index('ix_pedidos_estado_fecha', 'pedidos', ['estado', 'fecha'], unique=False)
    op.create_index(op.f('ix_pedidos_idempotency_key'), 'pedidos', ['idempotency_key'], unique=True)

    # Create pedido_items table
    op.create_table(
        'pedido_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('pedido_id', sa.BigInteger(), nullable=False),
        sa.Column('stock_id', sa.BigInteger(), nullable=False),
        sa.Column('variedad', sa.String(100), nullable=False),
        sa.Column('kilos', sa.Numeric(10, 3), nullable=False),
        sa.Column('precio_kg', sa.Numeric(12, 2), nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stock_id'], ['stock.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
    )
    op.create_index(op.f('ix_pedido_items_pedido_id'), 'pedido_items', ['pedido_id'], unique=False)
    op.create_index(op.f('ix_pedido_items_stock_id'), 'pedido_items', ['stock_id'], unique=False)
    op.execute("ALTER TABLE pedido_items ADD CONSTRAINT ck_pedido_items_kilos_positive CHECK (kilos > 0)")
    op.execute("ALTER TABLE pedido_items ADD CONSTRAINT ck_pedido_items_precio_positive CHECK (precio_kg > 0)")
    op.execute("ALTER TABLE pedido_items ADD CONSTRAINT ck_pedido_items_subtotal_non_negative CHECK (subtotal >= 0)")

    # Create pedido_estado_historial table
    op.create_table(
        'pedido_estado_historial',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('pedido_id', sa.BigInteger(), nullable=False),
        sa.Column('estado_anterior', sa.Enum('Pendiente', 'Listo', 'Entregado', name='estado_pedido_enum', create_constraint=False, native_enum=False), nullable=True),
        sa.Column('estado_nuevo', sa.Enum('Pendiente', 'Listo', 'Entregado', name='estado_pedido_enum', create_constraint=False, native_enum=False), nullable=False),
        sa.Column('usuario_id', sa.BigInteger(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
    )
    op.create_index('ix_pedido_estado_historial_pedido_timestamp', 'pedido_estado_historial', ['pedido_id', 'timestamp'], unique=False)

    # Add check constraint to pedidos
    op.execute("ALTER TABLE pedidos ADD CONSTRAINT ck_pedidos_total_non_negative CHECK (total >= 0)")


def downgrade() -> None:
    op.drop_table('pedido_estado_historial')
    op.drop_table('pedido_items')
    op.drop_table('pedidos')
    op.execute("DROP TYPE IF EXISTS estado_pedido_enum")