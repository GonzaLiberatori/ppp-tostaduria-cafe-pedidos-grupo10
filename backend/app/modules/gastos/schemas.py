from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class GastoBase(BaseModel):
    fecha: datetime
    categoria: str = Field(..., min_length=1, max_length=50)
    descripcion: str = Field(..., min_length=1)
    monto: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)


class GastoCreate(GastoBase):
    pass


class GastoUpdate(BaseModel):
    fecha: Optional[datetime] = Field(default=None)
    categoria: Optional[str] = Field(default=None, min_length=1, max_length=50)
    descripcion: Optional[str] = Field(default=None, min_length=1)
    monto: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)


class GastoRead(GastoBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)