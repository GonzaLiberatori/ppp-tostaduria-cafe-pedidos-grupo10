"""Modelos del módulo de ventas: cobro, pagos y auditoría de anulaciones.

Las tablas son propias (``venta_comercial``, ``pago_venta`` y
``venta_comercial_historial``) para no colisionar con las tablas heredadas
``venta`` y ``pago`` del módulo de pedidos, que siguen mapeadas allí y sin uso.

El pedido se referencia solo por clave foránea, sin ``relationship``: la venta
lo lee pero nunca lo modifica, así el mapeo no se acopla entre módulos.
"""

import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base

# Los enums se reutilizan desde pedidos para que la API exponga exactamente los
# mismos valores y no haya dos definiciones que puedan divergir.
from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda


class VentaEstado(str, enum.Enum):
    """Estado de una venta. Una venta anulada no se borra."""

    CONFIRMADA = "CONFIRMADA"
    ANULADA = "ANULADA"


class VentaComercial(Base):
    """Cobro registrado sobre un pedido entregado."""

    __tablename__ = "venta_comercial"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False, index=True)
    fecha = Column(DateTime, nullable=False)
    facturacion = Column(SQLEnum(Facturacion), nullable=False)
    estado = Column(SQLEnum(VentaEstado), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    # Se completa después del flush que asigna el id, por eso admite NULL.
    numero_comprobante = Column(String(20), nullable=True, unique=True, index=True)
    cuenta_id = Column(Integer, ForeignKey("cuenta.id"), nullable=True)
    creada_en = Column(DateTime, nullable=False)
    anulada_en = Column(DateTime, nullable=True)

    # Una sola venta vigente por pedido. El índice es parcial para permitir
    # volver a vender un pedido cuya venta anterior fue anulada.
    __table_args__ = (
        Index(
            "ux_venta_comercial_pedido_vigente",
            "pedido_id",
            unique=True,
            sqlite_where=text("estado = 'CONFIRMADA'"),
        ),
    )

    pagos = relationship(
        "PagoVenta",
        back_populates="venta",
        cascade="all, delete-orphan",
        order_by="PagoVenta.id",
    )
    historial = relationship(
        "VentaComercialHistorial",
        back_populates="venta",
        cascade="all, delete-orphan",
        order_by="VentaComercialHistorial.id",
    )

    def __repr__(self) -> str:
        return (
            f"<VentaComercial(id={self.id}, pedido_id={self.pedido_id}, "
            f"estado={self.estado})>"
        )


class PagoVenta(Base):
    """Pago con importe asociado a una venta."""

    __tablename__ = "pago_venta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    venta_id = Column(
        Integer, ForeignKey("venta_comercial.id"), nullable=False, index=True
    )
    metodo_de_pago = Column(SQLEnum(MetodoPago), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    moneda = Column(SQLEnum(Moneda), nullable=False)
    aclaracion = Column(String(255), nullable=True)
    creado_en = Column(DateTime, nullable=False)

    venta = relationship("VentaComercial", back_populates="pagos")


class VentaComercialHistorial(Base):
    """Auditoría de los cambios de estado de una venta."""

    __tablename__ = "venta_comercial_historial"

    id = Column(Integer, primary_key=True, autoincrement=True)
    venta_id = Column(
        Integer, ForeignKey("venta_comercial.id"), nullable=False, index=True
    )
    estado_anterior = Column(SQLEnum(VentaEstado), nullable=True)
    estado_nuevo = Column(SQLEnum(VentaEstado), nullable=False)
    motivo = Column(String(255), nullable=True)
    cuenta_id = Column(Integer, ForeignKey("cuenta.id"), nullable=True)
    timestamp = Column(DateTime, nullable=False)

    venta = relationship("VentaComercial", back_populates="historial")


__all__ = [
    "VentaEstado",
    "VentaComercial",
    "PagoVenta",
    "VentaComercialHistorial",
]
