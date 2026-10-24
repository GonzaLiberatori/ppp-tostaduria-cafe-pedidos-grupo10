from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    ADMINISTRADOR = "Administrador"
    CAJERO = "Cajero"
    OPERARIO = "Operario"
    CLIENTE = "Cliente"


class Cuenta(Base):
    __tablename__ = "cuenta"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rol = Column(SQLEnum(UserRole), nullable=False)
    correo = Column(String(100), unique=True, nullable=False, index=True)
    clave = Column(String(255), nullable=False)

    persona = relationship("Persona", back_populates="cuenta", uselist=False)