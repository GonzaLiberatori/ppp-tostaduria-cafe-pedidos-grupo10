from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum as PyEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EstadoPedidoEnum(str, PyEnum):
    PENDIENTE = "Pendiente"
    LISTO = "Listo"
    ENTREGADO = "Entregado"


class PedidoItemBase(BaseModel):
    stock_id: int = Field(..., gt=0, description="ID del stock (café tostado)")
    variedad: str = Field(..., min_length=1, max_length=100, description="Nombre de la variedad")
    kilos: Decimal = Field(..., gt=0, max_digits=10, decimal_places=3, description="Kilos solicitados")
    precio_kg: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="Precio por kilo")

    @field_validator("kilos", "precio_kg", mode="before")
    @classmethod
    def convert_to_decimal(cls, v):
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v


class PedidoItemCreate(PedidoItemBase):
    pass


class PedidoItemRead(PedidoItemBase):
    id: int
    pedido_id: int
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class PedidoBase(BaseModel):
    cliente_id: int = Field(..., gt=0, description="ID del cliente")
    medio_contacto: str = Field(default="WhatsApp", max_length=50)
    observaciones: Optional[str] = Field(default=None)
    estado: EstadoPedidoEnum = Field(default=EstadoPedidoEnum.PENDIENTE)


class PedidoCreate(PedidoBase):
    items: List[PedidoItemCreate] = Field(..., min_length=1, description="Al menos un item requerido")

    @field_validator("items")
    @classmethod
    def validate_items_not_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Debe haber al menos un item en el pedido")
        return v


class PedidoUpdate(BaseModel):
    medio_contacto: Optional[str] = Field(default=None, max_length=50)
    observaciones: Optional[str] = Field(default=None)
    estado: Optional[EstadoPedidoEnum] = Field(default=None)


class PedidoRead(BaseModel):
    id: int
    cliente_id: int
    fecha: datetime
    estado: EstadoPedidoEnum
    medio_contacto: str
    observaciones: Optional[str]
    total: Decimal
    idempotency_key: str
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


class PedidoDetailRead(PedidoRead):
    items: List[PedidoItemRead] = []
    cliente_nombre: Optional[str] = None
    cliente_tipo: Optional[str] = None


class PedidoListRead(BaseModel):
    id: int
    fecha: datetime
    cliente_id: int
    cliente_nombre: str
    estado: EstadoPedidoEnum
    items_count: int
    kilos_totales: Decimal
    total: Decimal
    medio_contacto: str

    model_config = ConfigDict(from_attributes=True)


class PedidoEstadoHistorialRead(BaseModel):
    id: int
    pedido_id: int
    estado_anterior: Optional[EstadoPedidoEnum]
    estado_nuevo: EstadoPedidoEnum
    usuario_id: Optional[int]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)