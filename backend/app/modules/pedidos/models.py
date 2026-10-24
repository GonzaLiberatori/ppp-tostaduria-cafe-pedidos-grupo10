from sqlalchemy import Column, Integer, String, ForeignKey, Date, Numeric, Enum as SQLEnum, DateTime, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class TipoCliente(str, enum.Enum):
    MAYORISTA = "Mayorista"
    CONSUMIDOR_FINAL = "Consumidor Final"


class TipoLote(str, enum.Enum):
    VERDE = "VERDE"
    TOSTADO = "TOSTADO"


class EstadoLote(str, enum.Enum):
    CERRADO = "CERRADO"
    ABIERTO = "ABIERTO"


class MetodoDespacho(str, enum.Enum):
    RETIRO_LOCAL = "Retiro en local"
    ENVIO_PROPIO = "Envio propio"
    TRANSPORTE_EXTERNO = "Transporte externo"


class EstadoPedido(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    LISTO = "LISTO"
    ENTREGADO = "ENTREGADO"


class PedidoEstadoHistorial(Base):
    __tablename__ = "pedido_estado_historial"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False, index=True)
    estado_anterior = Column(SQLEnum(EstadoPedido), nullable=True)
    estado_nuevo = Column(SQLEnum(EstadoPedido), nullable=False)
    usuario_id = Column(Integer, ForeignKey("cuenta.id"), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="historial_estados")


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


class Pais(Base):
    __tablename__ = "pais"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False)

    regiones = relationship("Region", back_populates="pais")


class Region(Base):
    __tablename__ = "region"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False)
    pais_id = Column(Integer, ForeignKey("pais.id"), nullable=False)

    pais = relationship("Pais", back_populates="regiones")
    tipos_cafe = relationship("TipoDeCafe", back_populates="region")


class Variedad(Base):
    __tablename__ = "variedad"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False)

    tipos_cafe = relationship("TipoDeCafe", back_populates="variedad")


class TipoDeCafe(Base):
    __tablename__ = "tipo_de_cafe"
    id = Column(Integer, primary_key=True, autoincrement=True)
    organico = Column(Integer, nullable=False)  # 0 o 1
    precio_por_kg_verde = Column(Numeric(10, 2), nullable=False)
    region_id = Column(Integer, ForeignKey("region.id"), nullable=False)
    variedad_id = Column(Integer, ForeignKey("variedad.id"), nullable=False)

    region = relationship("Region", back_populates="tipos_cafe")
    variedad = relationship("Variedad", back_populates="tipos_cafe")
    lotes = relationship("Lote", back_populates="tipo_de_cafe")
    blends = relationship("BlendHasTipoDeCafe", back_populates="tipo_de_cafe")
    detalles_pedido = relationship("DetallePedido", back_populates="tipo_de_cafe")


class Blend(Base):
    __tablename__ = "blend"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    precio_por_kg_verde = Column(Numeric(10, 2), nullable=False)
    descripcion = Column(Text, nullable=False)

    tipos_cafe = relationship("BlendHasTipoDeCafe", back_populates="blend")
    lotes = relationship("Lote", back_populates="blend")
    detalles_pedido = relationship("DetallePedido", back_populates="blend")


class BlendHasTipoDeCafe(Base):
    __tablename__ = "blend_has_tipo_de_cafe"
    blend_id = Column(Integer, ForeignKey("blend.id"), primary_key=True)
    tipo_de_cafe_id = Column(Integer, ForeignKey("tipo_de_cafe.id"), primary_key=True)
    porcentaje = Column(Numeric(5, 2), nullable=False)

    blend = relationship("Blend", back_populates="tipos_cafe")
    tipo_de_cafe = relationship("TipoDeCafe", back_populates="blends")


class Molienda(Base):
    __tablename__ = "molienda"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(String(50), unique=True, nullable=False)
    valor_agregado_por_kg = Column(Numeric(10, 2), nullable=False, default=0)

    detalles_pedido = relationship("DetallePedido", back_populates="molienda")


class PerfilDeTostado(Base):
    __tablename__ = "perfil_de_tostado"
    id = Column(Integer, primary_key=True, autoincrement=True)
    variante = Column(String(50), nullable=False)
    valor_agregado_por_kg = Column(Numeric(10, 2), nullable=False, default=0)

    ordenes_tueste = relationship("OrdenTueste", back_populates="perfil_de_tostado")
    detalles_pedido = relationship("DetallePedido", back_populates="perfil_de_tostado")


class OrdenTueste(Base):
    __tablename__ = "orden_tueste"
    id = Column(Integer, primary_key=True)
    fecha_tueste = Column(DateTime, nullable=False)
    kg_gastados = Column(Numeric(10, 2), nullable=False)
    kg_obtenidos = Column(Numeric(10, 2), nullable=False)
    perfil_de_tostado_id = Column(Integer, ForeignKey("perfil_de_tostado.id"), nullable=False)

    perfil_de_tostado = relationship("PerfilDeTostado", back_populates="ordenes_tueste")
    lotes = relationship("Lote", back_populates="orden_tueste")


class Lote(Base):
    __tablename__ = "lote"
    id = Column(Integer, primary_key=True)
    tipo = Column(SQLEnum(TipoLote), nullable=False)
    estado = Column(SQLEnum(EstadoLote), nullable=False)
    fecha_vencimiento = Column(DateTime, nullable=False)
    humedad = Column(Numeric(5, 2), nullable=False)
    kg_disponibles = Column(Numeric(10, 2), nullable=False)
    kg_reales = Column(Numeric(10, 2), nullable=False)
    ubicacion_fisica = Column(String(50), nullable=False)
    observaciones = Column(Text, nullable=True)
    tipo_de_cafe_id = Column(Integer, ForeignKey("tipo_de_cafe.id"), nullable=True)
    blend_id = Column(Integer, ForeignKey("blend.id"), nullable=True)
    orden_tueste_id = Column(Integer, ForeignKey("orden_tueste.id"), nullable=True)

    tipo_de_cafe = relationship("TipoDeCafe", back_populates="lotes")
    blend = relationship("Blend", back_populates="lotes")
    orden_tueste = relationship("OrdenTueste", back_populates="lotes")


class Persona(Base):
    __tablename__ = "persona"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(45), nullable=False)
    apellido = Column(String(45), nullable=False)
    CUIT = Column(String(15), unique=True, nullable=True)
    telefono = Column(String(25), unique=True, nullable=False)
    cuenta_id = Column(Integer, ForeignKey("cuenta.id"), nullable=True)

    cuenta = relationship("Cuenta", back_populates="persona")
    cliente = relationship("Cliente", back_populates="persona", uselist=False)
    empleado = relationship("Empleado", back_populates="persona", uselist=False)


class Cliente(Base):
    __tablename__ = "cliente"
    persona_id = Column(Integer, ForeignKey("persona.id"), primary_key=True)
    tipo = Column(SQLEnum(TipoCliente), nullable=False)
    direccion_de_entrega = Column(String(100), nullable=True)
    
    # Cuenta corriente
    saldo_cuenta_corriente = Column(Numeric(12, 2), nullable=False, default=0)
    limite_credito = Column(Numeric(12, 2), nullable=True)
    
    # Propiedad computada
    @property
    def es_b2b(self) -> bool:
        return self.tipo == TipoCliente.MAYORISTA

    persona = relationship("Persona", back_populates="cliente")
    pedidos = relationship("Pedido", back_populates="cliente")


class Empleado(Base):
    __tablename__ = "empleado"
    persona_id = Column(Integer, ForeignKey("persona.id"), primary_key=True)
    fecha_de_contratacion = Column(Date, nullable=False)
    fecha_de_nacimiento = Column(Date, nullable=False)
    salario = Column(Numeric(10, 2), nullable=False)

    persona = relationship("Persona", back_populates="empleado")
    pedidos = relationship("Pedido", back_populates="empleado")


class Pedido(Base):
    __tablename__ = "pedido"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(DateTime, nullable=False)
    metodo_de_despacho = Column(SQLEnum(MetodoDespacho), nullable=False)
    estado = Column(SQLEnum(EstadoPedido), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    idempotency_key = Column(String(64), unique=True, nullable=True, index=True)
    medio_contacto = Column(String(50), nullable=True)
    observaciones = Column(Text, nullable=True)
    cliente_persona_id = Column(Integer, ForeignKey("cliente.persona_id"), nullable=False)
    empleado_persona_id = Column(Integer, ForeignKey("empleado.persona_id"), nullable=False)

    cliente = relationship("Cliente", back_populates="pedidos")
    empleado = relationship("Empleado", back_populates="pedidos")
    detalles = relationship("DetallePedido", back_populates="pedido", cascade="all, delete-orphan")
    venta = relationship("Venta", back_populates="pedido", uselist=False)
    historial_estados = relationship("PedidoEstadoHistorial", back_populates="pedido", cascade="all, delete-orphan")


class DetallePedido(Base):
    __tablename__ = "detalle_pedido"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cantidad_kg = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False)
    tipo_de_cafe_id = Column(Integer, ForeignKey("tipo_de_cafe.id"), nullable=True)
    blend_id = Column(Integer, ForeignKey("blend.id"), nullable=True)
    molienda_id = Column(Integer, ForeignKey("molienda.id"), nullable=True)
    perfil_de_tostado_id = Column(Integer, ForeignKey("perfil_de_tostado.id"), nullable=True)

    pedido = relationship("Pedido", back_populates="detalles")
    tipo_de_cafe = relationship("TipoDeCafe", back_populates="detalles_pedido")
    blend = relationship("Blend", back_populates="detalles_pedido")
    molienda = relationship("Molienda", back_populates="detalles_pedido")
    perfil_de_tostado = relationship("PerfilDeTostado", back_populates="detalles_pedido")


class Pago(Base):
    __tablename__ = "pago"
    id = Column(Integer, primary_key=True, autoincrement=True)
    metodo_de_pago = Column(SQLEnum(MetodoPago), nullable=False)
    porcentaje_pagado = Column(Numeric(5, 2), nullable=False)
    moneda = Column(SQLEnum(Moneda), nullable=False)
    aclaracion = Column(String(50), nullable=True)

    ventas = relationship("Venta", back_populates="pago")


class Venta(Base):
    __tablename__ = "venta"
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, nullable=False)
    facturacion = Column(SQLEnum(Facturacion), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=False)
    pago_id = Column(Integer, ForeignKey("pago.id"), nullable=False)

    pedido = relationship("Pedido", back_populates="venta")
    pago = relationship("Pago", back_populates="ventas")