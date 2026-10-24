from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Enum as SQLEnum, DateTime, Text, Boolean, Date
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class TipoStock(str, enum.Enum):
    VERDE = "VERDE"
    TOSTADO = "TOSTADO"


class EstadoStock(str, enum.Enum):
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"
    RESERVADO = "RESERVADO"


class Stock(Base):
    __tablename__ = "stock"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(SQLEnum(TipoStock), nullable=False)
    estado = Column(SQLEnum(EstadoStock), nullable=False, default=EstadoStock.ABIERTO)
    fecha_creacion = Column(DateTime, nullable=False)
    fecha_vencimiento = Column(DateTime, nullable=True)
    kg_disponibles = Column(Numeric(10, 2), nullable=False, default=0)
    kg_reservados = Column(Numeric(10, 2), nullable=False, default=0)
    ubicacion = Column(String(100), nullable=True)
    observaciones = Column(Text, nullable=True)
    
    # Referencias opcionales a catálogos
    tipo_de_cafe_id = Column(Integer, ForeignKey("tipo_de_cafe.id"), nullable=True)
    blend_id = Column(Integer, ForeignKey("blend.id"), nullable=True)
    lote_id = Column(Integer, ForeignKey("lote.id"), nullable=True)
    
    # Relaciones
    tipo_de_cafe = relationship("TipoDeCafe", foreign_keys=[tipo_de_cafe_id])
    blend = relationship("Blend", foreign_keys=[blend_id])
    lote = relationship("Lote", foreign_keys=[lote_id])