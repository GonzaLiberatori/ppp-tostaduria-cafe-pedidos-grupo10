"""Schemas del módulo de clientes para el panel.

El panel trabaja con un contrato plano (``B2B``/``B2C``, deuda y kilos ya
calculados) mientras que el modelo canónico separa ``Persona``, ``Cliente`` y
la cuenta corriente. La traducción vive en ``services.py``.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_TIPOS_FRONTEND = {"B2B": "B2B", "B2C": "B2C"}
_TIPOS_CANONICOS = {
    "Mayorista": "B2B",
    "Consumidor Final": "B2C",
    "B2B": "B2B",
    "B2C": "B2C",
}


def normalizar_tipo_cliente(valor: str) -> str:
    """Devuelve B2B o B2C a partir de cualquiera de los dos vocabularios."""
    tipo = _TIPOS_CANONICOS.get((valor or "").strip())
    if tipo is None:
        raise ValueError("Tipo de cliente inválido. Debe ser B2B o B2C.")
    return tipo


class ClientePanelCreate(BaseModel):
    """Alta de cliente desde el panel.

    Acepta los campos que envía el formulario y descarta los calculados
    (``kilosComprados``) para no obligar al frontend a conocer el modelo.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    nombre: str = Field(min_length=1, max_length=90)
    tipo: str = Field(default="B2C")
    telefono: Optional[str] = Field(default=None, max_length=25)
    email: Optional[str] = Field(default=None, max_length=100)
    direccion: Optional[str] = Field(default=None, max_length=100)
    tieneDeuda: bool = False
    montoDeuda: Optional[Decimal] = Field(default=None, ge=0)
    limiteCredito: Optional[Decimal] = Field(default=None, ge=0)

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, valor: str) -> str:
        return normalizar_tipo_cliente(valor)


class ClientePanelUpdate(BaseModel):
    """Edición parcial de cliente desde el panel."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    nombre: Optional[str] = Field(default=None, min_length=1, max_length=90)
    tipo: Optional[str] = None
    telefono: Optional[str] = Field(default=None, max_length=25)
    email: Optional[str] = Field(default=None, max_length=100)
    direccion: Optional[str] = Field(default=None, max_length=100)
    tieneDeuda: Optional[bool] = None
    montoDeuda: Optional[Decimal] = Field(default=None, ge=0)
    limiteCredito: Optional[Decimal] = Field(default=None, ge=0)

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None
        return normalizar_tipo_cliente(valor)


class ClientePanelRead(BaseModel):
    """Cliente tal como lo consume el panel."""

    id: str
    nombre: str
    tipo: str
    telefono: str = ""
    email: str = ""
    direccion: str = ""
    kilosComprados: float = 0
    tieneDeuda: bool = False
    montoDeuda: float = 0
    limiteCredito: Optional[float] = None
    creadoEn: Optional[datetime] = None
