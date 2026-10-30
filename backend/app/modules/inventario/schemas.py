from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class BolsaBase(BaseModel):
    estado: str = Field(..., pattern="^(cerrada|abierta)$")
    kilos: Decimal = Field(..., gt=0, max_digits=10, decimal_places=3)
    lote_ref: str = Field(..., min_length=1, max_length=100)


class BolsaCreate(BolsaBase):
    pass


class BolsaRead(BolsaBase):
    id: str
    stock_id: int
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)


class StockBase(BaseModel):
    tipo: str = Field(..., pattern="^(verde|tostado)$")
    variedad: str = Field(..., min_length=1, max_length=100)
    origen: str = Field(..., min_length=1, max_length=100)
    precio_kg: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    lote_principal: str = Field(..., min_length=1, max_length=50)


class StockCreate(StockBase):
    pass


class StockUpdate(BaseModel):
    tipo: Optional[str] = Field(default=None, pattern="^(verde|tostado)$")
    variedad: Optional[str] = Field(default=None, min_length=1, max_length=100)
    origen: Optional[str] = Field(default=None, min_length=1, max_length=100)
    precio_kg: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    lote_principal: Optional[str] = Field(default=None, min_length=1, max_length=50)


class StockRead(StockBase):
    id: int
    fecha_ingreso: datetime
    bolsas: List[BolsaRead] = []

    model_config = ConfigDict(from_attributes=True)


class StockListRead(BaseModel):
    id: int
    tipo: str
    variedad: str
    origen: str
    precio_kg: Decimal
    lote_principal: str
    total_bolsas: int
    total_kilos: Decimal

    model_config = ConfigDict(from_attributes=True)