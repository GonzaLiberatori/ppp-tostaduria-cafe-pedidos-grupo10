"""Schemas del módulo de ventas: entrada y salida de la API."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.pedidos.models import Facturacion, MetodoPago, Moneda
from app.modules.ventas.models import VentaEstado

# Plazos admitidos para una venta a pagaré, en días.
PLAZOS_DE_PAGO: tuple[int, ...] = (30, 60, 90)


class CondicionPago(str, enum.Enum):
    """Cómo se paga la venta: al contado o con pagaré a plazo fijo.

    No se persiste: se deduce del estado y del vencimiento de la venta. Vive acá
    para que ``pedidos`` reenvíe el mismo contrato sin definir un enum propio.
    """

    CONTADO = "CONTADO"
    PAGARE = "PAGARE"


class PagoCreate(BaseModel):
    """Pago informado al registrar una venta."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    metodo_de_pago: MetodoPago
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    moneda: Moneda = Moneda.ARS
    aclaracion: Optional[str] = Field(default=None, max_length=255)


class VentaCreate(BaseModel):
    """Alta de venta sobre un pedido entregado.

    ``condicion_pago`` es opcional para no romper el contrato de 004: sin ella
    la venta se registra al contado con el método del primer pago.
    """

    model_config = ConfigDict(extra="ignore")

    pedido_id: int = Field(gt=0)
    facturacion: Facturacion
    pagos: list[PagoCreate] = Field(min_length=1)
    condicion_pago: CondicionPago = CondicionPago.CONTADO
    plazo_dias: Optional[int] = None

    @model_validator(mode="after")
    def validar_condicion_de_pago(self) -> "VentaCreate":
        """Exige plazo solo para pagaré y dentro de los plazos admitidos."""
        if self.condicion_pago is CondicionPago.PAGARE:
            if self.plazo_dias is None:
                raise ValueError(
                    "Una venta a pagaré necesita plazo_dias (30, 60 o 90)."
                )
            if self.plazo_dias not in PLAZOS_DE_PAGO:
                raise ValueError(
                    "El plazo del pagaré debe ser 30, 60 o 90 días "
                    f"(se recibió {self.plazo_dias})."
                )
        elif self.plazo_dias is not None:
            raise ValueError(
                "El plazo solo aplica a la condición de pago PAGARE."
            )
        return self


class VentaCobroCreate(BaseModel):
    """Cobro de una venta pendiente con el método real con el que se cobró."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    metodo_de_pago: MetodoPago
    aclaracion: Optional[str] = Field(default=None, max_length=255)


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
    fecha_vencimiento: Optional[datetime] = None
    cobrada_en: Optional[datetime] = None


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


class VentaResumenMensualRead(BaseModel):
    """Fila mensual del resumen de ventas que alimenta la contabilidad."""

    mes: str
    cantidad_ventas: int
    total_facturado: Decimal
    totales_por_metodo: list[ResumenPorMetodo] = Field(default_factory=list)


class VentaCobranzaMensualRead(BaseModel):
    """Cobranza de un mes, agrupada por el mes en que entró el dinero."""

    mes: str
    cantidad_cobros: int
    total_cobrado: Decimal
    totales_por_metodo: list[ResumenPorMetodo] = Field(default_factory=list)


class VentaPorCobrarItemRead(BaseModel):
    """Una venta pendiente de cobro, con su vencimiento y si está vencida."""

    venta_id: int
    pedido_id: int
    numero_comprobante: Optional[str] = None
    cliente_persona_id: Optional[int] = None
    cliente_nombre: Optional[str] = None
    fecha: datetime
    fecha_vencimiento: Optional[datetime] = None
    total: Decimal
    vencida: bool


class VentaPorCobrarRead(BaseModel):
    """Saldo por cobrar completo: pendientes, total y cantidad de vencidas."""

    items: list[VentaPorCobrarItemRead] = Field(default_factory=list)
    total_por_cobrar: Decimal
    cantidad_vencidas: int = 0


__all__ = [
    "PLAZOS_DE_PAGO",
    "CondicionPago",
    "PagoCreate",
    "VentaCreate",
    "VentaCobroCreate",
    "VentaAnulacionCreate",
    "PagoVentaRead",
    "VentaHistorialRead",
    "VentaRead",
    "VentaDetailRead",
    "VentaListRead",
    "ResumenPorMetodo",
    "VentaResumenRead",
    "VentaResumenMensualRead",
    "VentaCobranzaMensualRead",
    "VentaPorCobrarItemRead",
    "VentaPorCobrarRead",
]
