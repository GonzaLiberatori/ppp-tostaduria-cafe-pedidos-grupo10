"""Modelos del módulo de envíos programados (suscripciones B2B).

El módulo guarda dos cosas distintas:

- ``SuscripcionEnvio``: la configuración comercial acordada con el cliente
  (producto, kilos, día de la semana y plazo de pago).
- ``EntregaProgramada``: la ocurrencia concreta de un día. Su restricción
  ``UNIQUE (cliente_id, fecha_entrega)`` es la base de la idempotencia diaria:
  aunque el job corra dos veces, el mismo cliente no puede tener dos entregas
  para la misma fecha.
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class EstadoEntrega(str, enum.Enum):
    """Ciclo de vida de una entrega programada."""

    PROGRAMADA = "PROGRAMADA"
    GENERADA = "GENERADA"
    ERROR = "ERROR"
    CANCELADA = "CANCELADA"


class SuscripcionEnvio(Base):
    """Configuración de una entrega recurrente para un cliente B2B."""

    __tablename__ = "suscripcion_envio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(
        Integer, ForeignKey("cliente.persona_id"), nullable=False, index=True
    )
    tipo_de_cafe_id = Column(
        Integer, ForeignKey("tipo_de_cafe.id"), nullable=True
    )
    blend_id = Column(Integer, ForeignKey("blend.id"), nullable=True)
    cantidad_kg = Column(Numeric(10, 2), nullable=False)
    # 0 = lunes ... 6 = domingo, igual que ``datetime.date.weekday()``.
    dia_semana = Column(Integer, nullable=False)
    plazo_dias = Column(Integer, nullable=False, default=30)
    activa = Column(Boolean, nullable=False, default=True)
    fecha_inicio = Column(Date, nullable=False, default=date.today)
    observaciones = Column(Text, nullable=True)
    creada_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizada_en = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    cliente = relationship("Cliente")
    tipo_de_cafe = relationship("TipoDeCafe")
    blend = relationship("Blend")
    entregas = relationship("EntregaProgramada", back_populates="suscripcion")

    @property
    def producto(self) -> str:
        """Devuelve ``tipo`` o ``blend`` según el origen configurado."""
        return "tipo" if self.tipo_de_cafe_id is not None else "blend"

    @property
    def producto_id(self) -> Optional[int]:
        """Identificador del catálogo que se entrega."""
        return self.tipo_de_cafe_id or self.blend_id


class EntregaProgramada(Base):
    """Ocurrencia diaria de una suscripción, con su pedido generado."""

    __tablename__ = "entrega_programada"
    __table_args__ = (
        UniqueConstraint(
            "cliente_id",
            "fecha_entrega",
            name="uq_entrega_programada_cliente_fecha",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(
        Integer, ForeignKey("cliente.persona_id"), nullable=False, index=True
    )
    fecha_entrega = Column(Date, nullable=False, index=True)
    estado = Column(
        SQLEnum(EstadoEntrega), nullable=False, default=EstadoEntrega.PROGRAMADA
    )
    pedido_id = Column(Integer, ForeignKey("pedido.id"), nullable=True)
    suscripcion_id = Column(
        Integer, ForeignKey("suscripcion_envio.id"), nullable=True
    )
    generada_en = Column(DateTime, nullable=True)
    error = Column(String(255), nullable=True)
    creada_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    cliente = relationship("Cliente")
    pedido = relationship("Pedido")
    suscripcion = relationship("SuscripcionEnvio", back_populates="entregas")


__all__: List[str] = [
    "EstadoEntrega",
    "SuscripcionEnvio",
    "EntregaProgramada",
]
