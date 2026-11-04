"""Contratos Pydantic del módulo de envíos programados."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

PLAZOS_DE_PAGO = (30, 60, 90)
DIAS_DE_LA_SEMANA = (
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
)


class SuscripcionCreate(BaseModel):
    """Alta de una suscripción desde el panel o el portal del cliente."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    clienteId: str
    tipoDeCafeId: Optional[int] = None
    blendId: Optional[int] = None
    cantidadKg: Decimal = Field(gt=0)
    diaSemana: int = Field(ge=0, le=6)
    plazoDias: Literal[30, 60, 90] = 30
    fechaInicio: Optional[date] = None
    observaciones: str = ""

    @model_validator(mode="after")
    def validar_unico_producto(self) -> "SuscripcionCreate":
        """Exige exactamente un origen de producto por suscripción."""
        if (self.tipoDeCafeId is None) == (self.blendId is None):
            raise ValueError(
                "Hay que indicar tipoDeCafeId o blendId, pero no ambos."
            )
        return self


class SuscripcionUpdate(BaseModel):
    """Edición parcial de una suscripción."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    cantidadKg: Optional[Decimal] = Field(default=None, gt=0)
    diaSemana: Optional[int] = Field(default=None, ge=0, le=6)
    plazoDias: Optional[Literal[30, 60, 90]] = None
    activa: Optional[bool] = None
    observaciones: Optional[str] = None


class SuscripcionRead(BaseModel):
    """Suscripción tal como la consume el frontend."""

    id: int
    clienteId: str
    clienteNombre: str
    producto: Literal["tipo", "blend"]
    productoId: int
    variedad: str
    cantidadKg: float
    diaSemana: int
    diaNombre: str
    plazoDias: int
    activa: bool
    fechaInicio: date
    observaciones: str = ""


class EntregaRead(BaseModel):
    """Entrega concreta generada para una fecha."""

    id: int
    clienteId: str
    clienteNombre: str
    fechaEntrega: date
    estado: str
    pedidoId: Optional[str] = None
    generadaEn: Optional[datetime] = None
    error: Optional[str] = None


class HojaDeRutaItemRead(BaseModel):
    """Línea de pedido dentro de la hoja de ruta del día."""

    stockId: str
    variedad: str
    kilos: float
    precioKg: float
    subtotal: float


class HojaDeRutaRead(BaseModel):
    """Pedido generado para el reparto de una fecha."""

    pedidoId: str
    clienteId: str
    clienteNombre: str
    direccion: str
    telefono: str
    estado: str
    condicionPago: str
    total: float
    items: List[HojaDeRutaItemRead]


class GeneracionDetalle(BaseModel):
    """Resultado por cliente de una corrida de generación."""

    clienteId: str
    clienteNombre: str
    estado: Literal["GENERADA", "OMITIDA", "ERROR"]
    pedidoId: Optional[str] = None
    mensaje: Optional[str] = None


class GeneracionResultadoRead(BaseModel):
    """Resumen de la corrida diaria del job."""

    fecha: date
    procesadas: int
    generadas: int
    omitidas: int
    errores: int
    detalle: List[GeneracionDetalle]
