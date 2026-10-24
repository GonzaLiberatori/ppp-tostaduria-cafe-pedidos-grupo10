from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class PaisBase(BaseModel):
    nombre: str


class PaisCreate(PaisBase):
    pass


class PaisResponse(PaisBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RegionBase(BaseModel):
    nombre: str
    pais_id: int


class RegionCreate(RegionBase):
    pass


class RegionResponse(RegionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class VariedadBase(BaseModel):
    nombre: str


class VariedadCreate(VariedadBase):
    pass


class VariedadResponse(VariedadBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TipoDeCafeBase(BaseModel):
    organico: bool
    precio_por_kg_verde: Decimal
    region_id: int
    variedad_id: int


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


class DetallePedidoCreate(BaseModel):
    cantidad_kg: Decimal
    subtotal: Optional[Decimal] = None
    tipo_de_cafe_id: Optional[int] = None
    blend_id: Optional[int] = None
    molienda_id: Optional[int] = None
    perfil_de_tostado_id: Optional[int] = None


class DetallePedidoResponse(DetallePedidoBase):
    id: int
    pedido_id: int

    model_config = ConfigDict(from_attributes=True)


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
    cliente_persona_id: int
    empleado_persona_id: int
    detalles: List[DetallePedidoCreate]


class PedidoUpdate(BaseModel):
    estado: Optional[str] = None
    metodo_de_despacho: Optional[str] = None


class PedidoUpdateConDetalles(BaseModel):
    estado: Optional[str] = None
    metodo_de_despacho: Optional[str] = None
    detalles: List[DetallePedidoCreate]


class PedidoResponse(PedidoBase):
    id: int
    detalles: List[DetallePedidoResponse] = []
    cliente: Optional[ClienteResponse] = None

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


# Resolve forward references
ClienteResponse.model_rebuild()
EmpleadoResponse.model_rebuild()
PedidoResponse.model_rebuild()