"""Modelos del módulo de pedidos y ventas.

Los catálogos de café (``TipoDeCafe``, ``Blend``, ``Lote``) pertenecen al
módulo de inventario y se reexportan acá para que el resto del módulo y los
tests puedan seguir usando ``pedidos.models``. Lo mismo aplica a ``Persona``,
``Cliente`` y ``Empleado``, que pertenecen a clientes, y a los modelos de
tueste, que pertenecen a producción.
"""

import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.modules.clientes.models import (  # noqa: F401  (reexport)
    Cliente,
    Empleado,
    Persona,
    TipoCliente,
)
from app.modules.inventario.models import (  # noqa: F401  (reexport)
    Blend,
    BlendHasTipoDeCafe,
    Lote,
    LoteEstado,
    LoteTipo,
    TipoDeCafe,
)
from app.modules.produccion.models import (  # noqa: F401  (reexport)
    Molienda,
    OrdenTueste,
    PerfilDeTostado,
)

# Alias con los nombres históricos que usa este módulo.
TipoLote = LoteTipo
EstadoLote = LoteEstado


class MetodoDespacho(str, enum.Enum):
    RETIRO_LOCAL = "Retiro en local"
    ENVIO_PROPIO = "Envio propio"
    TRANSPORTE_EXTERNO = "Transporte externo"


class EstadoPedido(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    LISTO = "LISTO"
    ENTREGADO = "ENTREGADO"


class MetodoPago(str, enum.Enum):
    EFECTIVO = "EFECTIVO"
    CREDITO = "CREDITO"
    DEBITO = "DEBITO"
    TRANSFERENCIA = "TRANSFERENCIA"
    MERCADO_PAGO = "MERCADO_PAGO"
    CHEQUE = "CHEQUE"
    OTRO = "OTRO"


class Moneda(str, enum.Enum):
    ARS = "ARS"
    USD = "USD"
    EUR = "EUR"
    BRL = "BRL"


class Facturacion(str, enum.Enum):
    FACTURA_A = "Factura A"
    CONSUMIDOR_FINAL = "Consumidor Final"
    TICKET = "Ticket"
    NO_REQUIERE = "No requiere"


class PedidoEstadoHistorial(Base):
    """Auditoría de cambios de estado de un pedido."""

    __tablename__ = "pedido_estado_historial"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False, index=True)
    estado_anterior = Column(SQLEnum(EstadoPedido), nullable=True)
    estado_nuevo = Column(SQLEnum(EstadoPedido), nullable=False)
    usuario_id = Column(Integer, ForeignKey("cuenta.id"), nullable=True)
    timestamp = Column(DateTime, nullable=False)

    pedido = relationship("Pedido", back_populates="historial_estados")


class Pedido(Base):
    """Pedido de venta."""

    __tablename__ = "pedido"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(DateTime, nullable=False)
    metodo_de_despacho = Column(SQLEnum(MetodoDespacho), nullable=False)
    estado = Column(SQLEnum(EstadoPedido), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    idempotency_key = Column(String(64), unique=True, nullable=True, index=True)
    medio_contacto = Column(String(50), nullable=True)
    observaciones = Column(Text, nullable=True)
    cliente_persona_id = Column(
        Integer, ForeignKey("cliente.persona_id"), nullable=False
    )
    empleado_persona_id = Column(
        Integer, ForeignKey("empleado.persona_id"), nullable=True
    )

    cliente = relationship("Cliente", back_populates="pedidos")
    empleado = relationship("Empleado", back_populates="pedidos")
    detalles = relationship(
        "DetallePedido", back_populates="pedido", cascade="all, delete-orphan"
    )
    venta = relationship("Venta", back_populates="pedido", uselist=False)
    historial_estados = relationship(
        "PedidoEstadoHistorial",
        back_populates="pedido",
        cascade="all, delete-orphan",
    )


class DetallePedido(Base):
    """Ítem de un pedido."""

    __tablename__ = "detalle_pedido"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cantidad_kg = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False)
    tipo_de_cafe_id = Column(
        Integer, ForeignKey("tipo_de_cafe.id"), nullable=True
    )
    blend_id = Column(Integer, ForeignKey("blend.id"), nullable=True)
    molienda_id = Column(Integer, ForeignKey("molienda.id"), nullable=True)
    perfil_de_tostado_id = Column(
        Integer, ForeignKey("perfil_de_tostado.id"), nullable=True
    )

    pedido = relationship("Pedido", back_populates="detalles")
    tipo_de_cafe = relationship("TipoDeCafe")
    blend = relationship("Blend")
    molienda = relationship("Molienda", back_populates="detalles_pedido")
    perfil_de_tostado = relationship(
        "PerfilDeTostado", back_populates="detalles_pedido"
    )


class Pago(Base):
    """Pago asociado a una venta."""

    __tablename__ = "pago"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metodo_de_pago = Column(SQLEnum(MetodoPago), nullable=False)
    porcentaje_pagado = Column(Numeric(5, 2), nullable=False)
    moneda = Column(SQLEnum(Moneda), nullable=False)
    aclaracion = Column(String(50), nullable=True)

    ventas = relationship("Venta", back_populates="pago")


class Venta(Base):
    """Venta formal asociada a un pedido."""

    __tablename__ = "venta"

    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, nullable=False)
    facturacion = Column(SQLEnum(Facturacion), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False)
    pago_id = Column(Integer, ForeignKey("pago.id"), nullable=False)

    pedido = relationship("Pedido", back_populates="venta")
    pago = relationship("Pago", back_populates="ventas")


__all__ = [
    "TipoCliente",
    "TipoLote",
    "EstadoLote",
    "MetodoDespacho",
    "EstadoPedido",
    "MetodoPago",
    "Moneda",
    "Facturacion",
    "Persona",
    "Cliente",
    "Empleado",
    "TipoDeCafe",
    "Blend",
    "BlendHasTipoDeCafe",
    "Lote",
    "Molienda",
    "PerfilDeTostado",
    "OrdenTueste",
    "PedidoEstadoHistorial",
    "Pedido",
    "DetallePedido",
    "Pago",
    "Venta",
]
