from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ClienteBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    tipo: str = Field(..., pattern="^(B2B|B2C)$")
    telefono: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    direccion: Optional[str] = Field(default=None)


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    tipo: Optional[str] = Field(default=None, pattern="^(B2B|B2C)$")
    telefono: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    direccion: Optional[str] = Field(default=None)


class ClienteRead(BaseModel):
    id: int
    nombre: str
    tipo: str
    kilos_comprados: int
    tiene_deuda: bool
    monto_deuda: Decimal
    telefono: Optional[str]
    email: Optional[str]
    direccion: Optional[str]
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


class ClienteListRead(BaseModel):
    id: int
    nombre: str
    tipo: str
    kilos_comprados: int
    tiene_deuda: bool
    monto_deuda: Decimal

    model_config = ConfigDict(from_attributes=True)