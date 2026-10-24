from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Enum as SQLEnum, Boolean, Date, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class TipoCliente(str, enum.Enum):
    MAYORISTA = "Mayorista"
    CONSUMIDOR_FINAL = "Consumidor Final"


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
    
    # Relaciones
    persona = relationship("Persona", back_populates="cliente")
    pedidos = relationship("Pedido", back_populates="cliente")