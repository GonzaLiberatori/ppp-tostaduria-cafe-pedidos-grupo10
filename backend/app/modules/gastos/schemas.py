"""Schemas del módulo de gastos para el panel de contabilidad."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GastoPanelCreate(BaseModel):
    """Alta de gasto enviada por el formulario del panel."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    categoria: str = Field(min_length=1, max_length=50)
    descripcion: str = Field(min_length=1)
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    fecha: datetime


class GastoPanelUpdate(BaseModel):
    """Edición parcial de gasto."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    categoria: Optional[str] = Field(default=None, min_length=1, max_length=50)
    descripcion: Optional[str] = Field(default=None, min_length=1)
    monto: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    fecha: Optional[datetime] = None


class GastoPanelRead(BaseModel):
    """Gasto tal como lo consume el panel."""

    id: str
    categoria: str
    descripcion: str
    monto: float
    fecha: datetime
