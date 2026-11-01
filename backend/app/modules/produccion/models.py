"""Modelos del módulo de producción (tueste y molienda)."""

from decimal import Decimal

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
    """Orden de tueste que convierte café verde en café tostado."""

    __tablename__ = "orden_tueste"

    id = Column(Integer, primary_key=True)
    fecha_tueste = Column(DateTime, nullable=False)
    kg_gastados = Column(Numeric(10, 2), nullable=False)
    kg_obtenidos = Column(Numeric(10, 2), nullable=False)
    perfil_de_tostado_id = Column(
        Integer, ForeignKey("perfil_de_tostado.id"), nullable=False
    )

    perfil_de_tostado = relationship("PerfilDeTostado", back_populates="ordenes_tueste")


__all__ = ["Molienda", "PerfilDeTostado", "OrdenTueste"]
