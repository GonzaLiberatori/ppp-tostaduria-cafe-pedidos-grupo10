"""Contratos planos del panel de stock.

El panel muestra "cafés" con bolsas, mientras que el modelo canónico tiene
``TipoDeCafe``/``Blend`` como origen y ``Lote`` como bolsa. Estos schemas son
la traducción de ida y vuelta que consume el frontend y viven aparte de
``schemas.py`` para no alterar la superficie canónica del módulo.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

_LONGITUD_NOMBRE = 50


class BolsaPanelCreate(BaseModel):
    """Bolsa inicial o adicional enviada por el panel."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    estado: str = Field(default="cerrada", description="cerrada o abierta.")
    kilos: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    loteRef: Optional[str] = Field(default=None, max_length=_LONGITUD_NOMBRE)


class BolsaPanelUpdate(BaseModel):
    """Edición parcial de una bolsa."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    estado: Optional[str] = Field(default=None, description="cerrada o abierta.")
    kilos: Optional[Decimal] = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="Kilos disponibles; 0 vacía la bolsa.",
    )
    loteRef: Optional[str] = Field(default=None, max_length=_LONGITUD_NOMBRE)


class StockPanelCreate(BaseModel):
    """Alta de un café con sus bolsas iniciales."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    tipo: str = Field(description="verde o tostado.")
    variedad: str = Field(min_length=1, max_length=_LONGITUD_NOMBRE)
    origen: str = Field(min_length=1, max_length=100)
    precioKg: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    lotePrincipal: str = Field(min_length=1, max_length=_LONGITUD_NOMBRE)
    bolsas: list[BolsaPanelCreate] = Field(min_length=1)


class StockPanelUpdate(BaseModel):
    """Edición parcial de un café del panel."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    tipo: Optional[str] = None
    variedad: Optional[str] = Field(default=None, min_length=1, max_length=_LONGITUD_NOMBRE)
    origen: Optional[str] = Field(default=None, min_length=1, max_length=100)
    precioKg: Optional[Decimal] = Field(
        default=None, gt=0, max_digits=10, decimal_places=2
    )
    lotePrincipal: Optional[str] = Field(
        default=None, min_length=1, max_length=_LONGITUD_NOMBRE
    )


class BolsaPanelRead(BaseModel):
    """Bolsa tal como la consume el panel."""

    id: str
    estado: str
    kilos: float
    fechaCreacion: datetime
    loteRef: str


class StockPanelRead(BaseModel):
    """Café con sus bolsas tal como lo consume el panel."""

    id: str
    tipo: str
    variedad: str
    origen: str
    precioKg: float
    lotePrincipal: str
    fechaIngreso: datetime
    bolsas: list[BolsaPanelRead]
