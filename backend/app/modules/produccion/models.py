"""Modelos del módulo de producción (tueste y molienda)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Molienda(Base):
    """Tipo de molienda y su valor agregado por kilo."""

    __tablename__ = "molienda"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(String(50), unique=True, nullable=False)
    valor_agregado_por_kg = Column(Numeric(10, 2), nullable=False, default=0)

    detalles_pedido = relationship("DetallePedido", back_populates="molienda")


class PerfilDeTostado(Base):
    """Perfil de tueste y su valor agregado por kilo."""

    __tablename__ = "perfil_de_tostado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    variante = Column(String(50), nullable=False)
    valor_agregado_por_kg = Column(Numeric(10, 2), nullable=False, default=0)

    ordenes_tueste = relationship("OrdenTueste", back_populates="perfil_de_tostado")
    detalles_pedido = relationship("DetallePedido", back_populates="perfil_de_tostado")


class OrdenTueste(Base):
    """Orden de tueste que convierte café verde en café tostado.

    Los kilos se guardan con tres decimales para que la conversión desde
    gramos sea exacta. ``tipo_de_cafe_id`` identifica la materia prima que se
    procesó y ``perfil_de_tostado_id`` queda opcional: el alta operativa de
    tueste no exige elegir un perfil comercial.
    """

    __tablename__ = "orden_tueste"

    id = Column(Integer, primary_key=True)
    fecha_tueste = Column(DateTime, nullable=False, default=datetime.now)
    kg_gastados = Column(Numeric(12, 3), nullable=False)
    kg_obtenidos = Column(Numeric(12, 3), nullable=False)
    tipo_de_cafe_id = Column(
        Integer, ForeignKey("tipo_de_cafe.id"), nullable=True, index=True
    )
    perfil_de_tostado_id = Column(
        Integer, ForeignKey("perfil_de_tostado.id"), nullable=True
    )

    tipo_de_cafe = relationship("TipoDeCafe")
    perfil_de_tostado = relationship("PerfilDeTostado", back_populates="ordenes_tueste")
    lotes = relationship("Lote", back_populates="orden_tueste")
    consumos = relationship(
        "ConsumoTueste",
        back_populates="orden_tueste",
        cascade="all, delete-orphan",
        order_by="ConsumoTueste.id",
    )

    @property
    def gramos_gastados(self) -> int:
        """Gramos de café verde consumidos, derivados de los kilos guardados."""
        return int((Decimal(self.kg_gastados) * 1000).to_integral_value())

    @property
    def gramos_obtenidos(self) -> int:
        """Gramos de café tostado obtenidos, derivados de los kilos guardados."""
        return int((Decimal(self.kg_obtenidos) * 1000).to_integral_value())

    @property
    def merma_gramos(self) -> int:
        """Diferencia entre lo que entró verde y lo que salió tostado."""
        return self.gramos_gastados - self.gramos_obtenidos

    @property
    def merma_porcentaje(self) -> Decimal:
        """Porcentaje de merma sobre el café verde procesado."""
        if self.gramos_gastados == 0:
            return Decimal("0")
        return (
            Decimal(self.merma_gramos) * Decimal("100") / Decimal(self.gramos_gastados)
        ).quantize(Decimal("0.01"))

    @property
    def lote_tostado_id(self) -> Optional[int]:
        """Id del lote tostado generado por la orden, si ya existe."""
        return self.lotes[0].id if self.lotes else None


class ConsumoTueste(Base):
    """Detalle de los lotes verdes consumidos por una orden de tueste.

    Es la trazabilidad de qué lote de materia prima se descontó y cuánto, sin
    depender de reconstruir el movimiento a partir del stock actual.
    """

    __tablename__ = "consumo_tueste"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_tueste_id = Column(
        Integer, ForeignKey("orden_tueste.id"), nullable=False, index=True
    )
    lote_id = Column(Integer, ForeignKey("lote.id"), nullable=False, index=True)
    kg_consumidos = Column(Numeric(12, 3), nullable=False)

    orden_tueste = relationship("OrdenTueste", back_populates="consumos")
    lote = relationship("Lote")

    @property
    def gramos_consumidos(self) -> int:
        """Gramos consumidos del lote verde, derivados de los kilos guardados."""
        return int((Decimal(self.kg_consumidos) * 1000).to_integral_value())


__all__ = ["Molienda", "PerfilDeTostado", "OrdenTueste", "ConsumoTueste"]
