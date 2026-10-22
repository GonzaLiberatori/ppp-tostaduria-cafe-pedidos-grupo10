from enum import Enum as PyEnum
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects import sqlite

from app.core.database import Base


class EstadoPedidoEnum(str, PyEnum):
    PENDIENTE = "Pendiente"
    LISTO = "Listo"
    ENTREGADO = "Entregado"


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    estado: Mapped[EstadoPedidoEnum] = mapped_column(
        Enum(
            EstadoPedidoEnum,
            name="estado_pedido_enum",
            create_constraint=False,  # Disable CHECK constraint for SQLite compatibility
            validate_strings=True,
            native_enum=False,
        ),
        nullable=False,
        default=EstadoPedidoEnum.PENDIENTE,
        index=True,
    )
    medio_contacto: Mapped[str] = mapped_column(String(50), nullable=False, default="WhatsApp")
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    items: Mapped[List["PedidoItem"]] = relationship(
        "PedidoItem",
        back_populates="pedido",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    historial_estados: Mapped[List["PedidoEstadoHistorial"]] = relationship(
        "PedidoEstadoHistorial",
        back_populates="pedido",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # cliente relationship will be added when Cliente model exists (string FK is defined on column)

    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_pedidos_total_non_negative"),
        Index("ix_pedidos_cliente_fecha", "cliente_id", "fecha"),
        Index("ix_pedidos_estado_fecha", "estado", "fecha"),
    )

    def __repr__(self) -> str:
        return f"<Pedido(id={self.id}, cliente_id={self.cliente_id}, estado={self.estado}, total={self.total})>"


class PedidoItem(Base):
    __tablename__ = "pedido_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pedido_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pedidos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("stock.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    variedad: Mapped[str] = mapped_column(String(100), nullable=False)
    kilos: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
    )
    precio_kg: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    pedido = relationship("Pedido", back_populates="items", lazy="selectin")

    __table_args__ = (
        CheckConstraint("kilos > 0", name="ck_pedido_items_kilos_positive"),
        CheckConstraint("precio_kg > 0", name="ck_pedido_items_precio_positive"),
        CheckConstraint("subtotal >= 0", name="ck_pedido_items_subtotal_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<PedidoItem(id={self.id}, pedido_id={self.pedido_id}, variedad={self.variedad}, kilos={self.kilos})>"


class PedidoEstadoHistorial(Base):
    __tablename__ = "pedido_estado_historial"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pedido_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pedidos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    estado_anterior: Mapped[Optional[EstadoPedidoEnum]] = mapped_column(
        Enum(
            EstadoPedidoEnum,
            name="estado_pedido_enum",
            create_constraint=False,
            native_enum=False,
        ),
        nullable=True,
    )
    estado_nuevo: Mapped[EstadoPedidoEnum] = mapped_column(
        Enum(
            EstadoPedidoEnum,
            name="estado_pedido_enum",
            create_constraint=False,
            native_enum=False,
        ),
        nullable=False,
    )
    usuario_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    pedido = relationship("Pedido", back_populates="historial_estados", lazy="selectin")

    __table_args__ = (
        Index("ix_pedido_estado_historial_pedido_timestamp", "pedido_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<PedidoEstadoHistorial(pedido_id={self.pedido_id}, {self.estado_anterior} -> {self.estado_nuevo})>"