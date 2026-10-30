"""Modelos del módulo de clientes, personas y cuentas corrientes."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class TipoCliente(str, enum.Enum):
    """Tipo comercial del cliente."""

    MAYORISTA = "Mayorista"
    CONSUMIDOR_FINAL = "Consumidor Final"


class Persona(Base):
    """Datos personales compartidos por clientes y empleados."""

    __tablename__ = "persona"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(45), nullable=False)
    apellido = Column(String(45), nullable=False)
    CUIT = Column(String(15), unique=True, nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    telefono = Column(String(25), unique=True, nullable=True)
    cuenta_id = Column(Integer, ForeignKey("cuenta.id"), nullable=True)

    cuenta = relationship("Cuenta", back_populates="persona")
    cliente = relationship("Cliente", back_populates="persona", uselist=False)
    empleado = relationship("Empleado", back_populates="persona", uselist=False)


class Cliente(Base):
    """Cliente con su cuenta corriente y límite de crédito."""

    __tablename__ = "cliente"

    persona_id = Column(Integer, ForeignKey("persona.id"), primary_key=True)
    tipo = Column(SQLEnum(TipoCliente), nullable=False)
    direccion_de_entrega = Column(String(100), nullable=True)
    fecha_alta = Column(DateTime, nullable=True, default=datetime.utcnow)

    # Cuenta corriente
    saldo_cuenta_corriente = Column(Numeric(12, 2), nullable=False, default=0)
    limite_credito = Column(Numeric(12, 2), nullable=True)

    persona = relationship("Persona", back_populates="cliente")
    pedidos = relationship("Pedido", back_populates="cliente")

    @property
    def es_b2b(self) -> bool:
        """Indica si el cliente es mayorista (B2B)."""
        return self.tipo == TipoCliente.MAYORISTA


class Empleado(Base):
    """Empleado que puede registrar pedidos."""

    __tablename__ = "empleado"

    persona_id = Column(Integer, ForeignKey("persona.id"), primary_key=True)
    fecha_de_contratacion = Column(Date, nullable=False)
    fecha_de_nacimiento = Column(Date, nullable=False)
    salario = Column(Numeric(10, 2), nullable=False)

    persona = relationship("Persona", back_populates="empleado")
    pedidos = relationship("Pedido", back_populates="empleado")


__all__ = ["TipoCliente", "Persona", "Cliente", "Empleado"]
