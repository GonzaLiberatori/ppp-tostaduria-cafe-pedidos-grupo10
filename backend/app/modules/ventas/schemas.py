"""Schemas del módulo de ventas: entrada y salida de la API."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda
from app.modules.ventas.models import VentaEstado


class PagoCreate(BaseModel):
    """Pago informado al registrar una venta."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    metodo_de_pago: MetodoPago
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    moneda: Moneda = Moneda.ARS
    aclaracion: Optional[str] = Field(default=None, max_length=255)


class VentaCreate(BaseModel):
    """Alta de venta sobre un pedido entregado."""

    model_config = ConfigDict(extra="ignore")

    pedido_id: int = Field(gt=0)
    facturacion: Facturacion
    pagos: list[PagoCreate] = Field(min_length=1)


class VentaAnulacionCreate(BaseModel):
    """Motivo de la anulación lógica de una venta."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    motivo: str = Field(min_length=1, max_length=255)


class PagoVentaRead(BaseModel):
    """Pago guardado, tal como lo devuelve la API."""

    metodo_de_pago: MetodoPago
    monto: Decimal
    moneda: Moneda
    aclaracion: Optional[str] = None


class VentaHistorialRead(BaseModel):
    """Entrada de auditoría de una venta."""

    estado_anterior: Optional[VentaEstado] = None
    estado_nuevo: VentaEstado
    motivo: Optional[str] = None
    cuenta_id: Optional[int] = None
    timestamp: datetime


class VentaRead(BaseModel):
    """Datos base de una venta."""

    id: int
    pedido_id: int
    numero_comprobante: Optional[str] = None
    fecha: datetime
    facturacion: Facturacion
    estado: VentaEstado
    total: Decimal
    creada_en: datetime
    anulada_en: Optional[datetime] = None


class VentaDetailRead(VentaRead):
    """Venta con su pedido, cliente, pagos e historial."""

    cuenta_id: Optional[int] = None
    cliente_persona_id: Optional[int] = None
    cliente_nombre: Optional[str] = None
    pedido_estado: Optional[str] = None
    pedido_total: Optional[Decimal] = None
    pagos: list[PagoVentaRead] = Field(default_factory=list)
    historial: list[VentaHistorialRead] = Field(default_factory=list)


class VentaListRead(VentaRead):
    """Fila del listado de ventas."""

    cliente_persona_id: Optional[int] = None
    cliente_nombre: Optional[str] = None
    metodos_de_pago: list[MetodoPago] = Field(default_factory=list)


class ResumenPorMetodo(BaseModel):
    """Total cobrado con un método de pago en el rango consultado."""

    metodo_de_pago: MetodoPago
    monto: Decimal


class VentaResumenRead(BaseModel):
    """Arqueo de caja de un rango de fechas."""

    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None
    cantidad_ventas: int
    total_facturado: Decimal
    totales_por_metodo: list[ResumenPorMetodo] = Field(default_factory=list)


__all__ = [
    "PagoCreate",
    "VentaCreate",
    "VentaAnulacionCreate",
    "PagoVentaRead",
    "VentaHistorialRead",
    "VentaRead",
    "VentaDetailRead",
    "VentaListRead",
    "ResumenPorMetodo",
    "VentaResumenRead",
]
