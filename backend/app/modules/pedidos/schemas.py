from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class EstadoPedidoEnum(str):
    PENDIENTE = "PENDIENTE"
    LISTO = "LISTO"
    ENTREGADO = "ENTREGADO"


class TipoDeCafeBase(BaseModel):
    organico: bool
    precio_por_kg_verde: Decimal
    variedad: str
    region: str
    pais: str


class TipoDeCafeCreate(TipoDeCafeBase):
    pass


class TipoDeCafeResponse(TipoDeCafeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class BlendBase(BaseModel):
    nombre: str
    precio_por_kg_verde: Decimal
    descripcion: str


class BlendCreate(BlendBase):
    id: int


class BlendResponse(BlendBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class BlendHasTipoDeCafeBase(BaseModel):
    blend_id: int
    tipo_de_cafe_id: int
    porcentaje: Decimal


class BlendHasTipoDeCafeCreate(BlendHasTipoDeCafeBase):
    pass


class BlendHasTipoDeCafeResponse(BlendHasTipoDeCafeBase):
    model_config = ConfigDict(from_attributes=True)


class MoliendaBase(BaseModel):
    tipo: str
    valor_agregado_por_kg: Decimal = Decimal("0")


class MoliendaCreate(MoliendaBase):
    pass


class MoliendaResponse(MoliendaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PerfilDeTostadoBase(BaseModel):
    variante: str
    valor_agregado_por_kg: Decimal = Decimal("0")


class PerfilDeTostadoCreate(PerfilDeTostadoBase):
    pass


class PerfilDeTostadoResponse(PerfilDeTostadoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class OrdenTuesteBase(BaseModel):
    fecha_tueste: datetime
    kg_gastados: Decimal
    kg_obtenidos: Decimal
    perfil_de_tostado_id: int


class OrdenTuesteCreate(OrdenTuesteBase):
    id: int


class OrdenTuesteResponse(OrdenTuesteBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class LoteBase(BaseModel):
    tipo: str  # VERDE, TOSTADO
    estado: str  # CERRADO, ABIERTO
    fecha_vencimiento: datetime
    humedad: Decimal
    kg_disponibles: Decimal
    kg_reales: Decimal
    ubicacion_fisica: str
    observaciones: Optional[str] = None
    tipo_de_cafe_id: Optional[int] = None
    blend_id: Optional[int] = None
    orden_tueste_id: Optional[int] = None


class LoteCreate(LoteBase):
    id: int


class LoteResponse(LoteBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PersonaBase(BaseModel):
    nombre: str
    apellido: str
    CUIT: Optional[str] = None
    telefono: str


class PersonaCreate(PersonaBase):
    cuenta_id: Optional[int] = None


class PersonaResponse(PersonaBase):
    id: int
    cuenta_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ClienteBase(BaseModel):
    tipo: str  # Mayorista, Consumidor Final
    direccion_de_entrega: Optional[str] = None


class ClienteCreate(ClienteBase):
    persona_id: int


class ClienteResponse(ClienteBase):
    persona_id: int
    persona: Optional["PersonaResponse"] = None

    model_config = ConfigDict(from_attributes=True)


class EmpleadoBase(BaseModel):
    fecha_de_contratacion: datetime
    fecha_de_nacimiento: datetime
    salario: Decimal


class EmpleadoCreate(EmpleadoBase):
    persona_id: int


class EmpleadoResponse(EmpleadoBase):
    persona_id: int
    persona: Optional["PersonaResponse"] = None

    model_config = ConfigDict(from_attributes=True)


class DetallePedidoBase(BaseModel):
    cantidad_kg: Decimal
    subtotal: Decimal
    tipo_de_cafe_id: Optional[int] = None
    blend_id: Optional[int] = None
    molienda_id: Optional[int] = None
    perfil_de_tostado_id: Optional[int] = None


class DetallePedidoResponse(DetallePedidoBase):
    id: int
    pedido_id: int

    model_config = ConfigDict(from_attributes=True)


class DetallePedidoCreate(DetallePedidoBase):
    subtotal: Optional[Decimal] = None


class PedidoBase(BaseModel):
    fecha: datetime
    metodo_de_despacho: str  # Retiro en local, Envio propio, Transporte externo
    estado: str  # PENDIENTE, LISTO, ENTREGADO
    total: Decimal
    cliente_persona_id: int
    empleado_persona_id: int


class PedidoCreate(BaseModel):
    fecha: datetime
    metodo_de_despacho: str
    estado: str = "PENDIENTE"
    total: Optional[Decimal] = None
    idempotency_key: Optional[str] = None
    medio_contacto: Optional[str] = None
    observaciones: Optional[str] = None
    cliente_persona_id: int
    empleado_persona_id: int
    detalles: List[DetallePedidoCreate]

    @field_validator('detalles')
    @classmethod
    def validar_detalles_no_vacios(cls, v):
        if not v or len(v) == 0:
            raise ValueError("El pedido debe tener al menos un item")
        return v


class PedidoUpdate(BaseModel):
    estado: Optional[str] = None
    metodo_de_despacho: Optional[str] = None
    observaciones: Optional[str] = None
    medio_contacto: Optional[str] = None

    @field_validator('estado')
    @classmethod
    def validar_estado(cls, v):
        if v is not None and v not in ["PENDIENTE", "LISTO", "ENTREGADO"]:
            raise ValueError("Estado inválido. Debe ser PENDIENTE, LISTO o ENTREGADO")
        return v


class PedidoUpdateConDetalles(BaseModel):
    estado: Optional[str] = None
    metodo_de_despacho: Optional[str] = None
    observaciones: Optional[str] = None
    medio_contacto: Optional[str] = None
    detalles: List[DetallePedidoCreate]


class PedidoDetailRead(BaseModel):
    id: int
    fecha: datetime
    metodo_de_despacho: str
    estado: str
    total: Decimal
    idempotency_key: Optional[str] = None
    medio_contacto: Optional[str] = None
    observaciones: Optional[str] = None
    cliente_persona_id: int
    empleado_persona_id: int
    detalles: List[DetallePedidoResponse] = []
    cliente: Optional["ClienteResponse"] = None
    historial_estados: List["PedidoEstadoHistorialRead"] = []

    model_config = ConfigDict(from_attributes=True)


class PedidoListRead(BaseModel):
    id: int
    fecha: datetime
    metodo_de_despacho: str
    estado: str
    total: Decimal
    cliente_persona_id: int
    items_count: int = 0
    kilos_totales: Decimal = Decimal("0")
    medio_contacto: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PedidoResponse(BaseModel):
    id: int
    fecha: datetime
    metodo_de_despacho: str
    estado: str
    total: Decimal
    idempotency_key: Optional[str] = None
    medio_contacto: Optional[str] = None
    observaciones: Optional[str] = None
    cliente_persona_id: int
    empleado_persona_id: int
    detalles: List["DetallePedidoResponse"] = []
    cliente: Optional["ClienteResponse"] = None

    model_config = ConfigDict(from_attributes=True)


class PagoBase(BaseModel):
    metodo_de_pago: str  # EFECTIVO, CREDITO, DEBITO, TRANSFERENCIA, MERCADO_PAGO, CHEQUE, OTRO
    porcentaje_pagado: Decimal
    moneda: str  # ARS, USD, EUR, BRL
    aclaracion: Optional[str] = None


class PagoCreate(PagoBase):
    pass


class PagoResponse(PagoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class VentaBase(BaseModel):
    fecha: datetime
    facturacion: str  # Factura A, Consumidor Final, Ticket, No requiere
    pedido_id: int
    pago_id: int


class VentaCreate(VentaBase):
    id: int


class VentaResponse(VentaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PedidoEstadoHistorialRead(BaseModel):
    id: int
    pedido_id: int
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    usuario_id: Optional[int] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class PedidoDetailRead(BaseModel):
    id: int
    fecha: datetime
    metodo_de_despacho: str
    estado: str
    total: Decimal
    idempotency_key: Optional[str] = None
    medio_contacto: Optional[str] = None
    observaciones: Optional[str] = None
    cliente_persona_id: int
    empleado_persona_id: int
    detalles: List["DetallePedidoResponse"] = []
    cliente: Optional["ClienteResponse"] = None
    historial_estados: List["PedidoEstadoHistorialRead"] = []

    model_config = ConfigDict(from_attributes=True)


class PedidoListRead(BaseModel):
    id: int
    fecha: datetime
    metodo_de_despacho: str
    estado: str
    total: Decimal
    cliente_persona_id: int
    items_count: int = 0
    kilos_totales: Decimal = Decimal("0")
    medio_contacto: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Resolve forward references
ClienteResponse.model_rebuild()
EmpleadoResponse.model_rebuild()
PedidoCreate.model_rebuild()
PedidoResponse.model_rebuild()