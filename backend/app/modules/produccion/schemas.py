"""Schemas Pydantic del módulo de producción.

El alta operativa de un tueste se expresa en gramos porque es la unidad con la
que se pesa en planta. La persistencia sigue siendo en kilos con tres
decimales, de modo que la conversión no pierda precisión.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Espejo de las columnas Numeric(12, 3) de models.py.
KilosDeTueste = Annotated[
    Decimal, Field(max_digits=12, decimal_places=3, ge=0)
]
HumedadPorcentaje = Annotated[
    Decimal, Field(max_digits=5, decimal_places=2, ge=0, le=100)
]

# Tope defensivo: 999.999.999.999 gramos equivalen al máximo de la columna
# Numeric(12, 3) expresado en gramos.
_MAXIMO_GRAMOS = 999_999_999_999


class TuesteCreate(BaseModel):
    """Alta de una orden de tueste.

    Solo exige las tres magnitudes del proceso: gramos verdes consumidos,
    gramos tostados obtenidos y tipo de café. Los datos del lote resultante
    son opcionales y tienen valores operativos por defecto en el servicio.
    """

    model_config = ConfigDict(extra="forbid")

    gramos_verde: int = Field(
        gt=0,
        le=_MAXIMO_GRAMOS,
        description="Gramos de café verde que entran al tostador.",
    )
    gramos_tostado: int = Field(
        gt=0,
        le=_MAXIMO_GRAMOS,
        description="Gramos de café tostado que se obtienen del proceso.",
    )
    tipo_de_cafe_id: int = Field(
        gt=0,
        description="Identificador del tipo de café verde que se procesa.",
    )
    fecha_vencimiento: Optional[datetime] = Field(
        default=None,
        description="Vencimiento del lote tostado; por defecto, un año desde el tueste.",
    )
    humedad: Optional[HumedadPorcentaje] = Field(
        default=None,
        description="Humedad del lote tostado; si no se informa, se guarda 0.",
    )
    ubicacion_fisica: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Ubicación del lote tostado; por defecto, Producción.",
    )
    observaciones: Optional[str] = Field(
        default=None,
        description="Observaciones libres del lote tostado.",
    )

    @model_validator(mode="after")
    def _tostado_no_supera_verde(self) -> "TuesteCreate":
        """La materia prima no puede rendir más de lo que entró al tostador."""
        if self.gramos_tostado > self.gramos_verde:
            raise ValueError(
                "Los gramos tostados no pueden superar los gramos verdes consumidos."
            )
        return self


class ConsumoLoteRead(BaseModel):
    """Lote verde consumido por una orden de tueste."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    lote_id: int = Field(description="Identificador del lote verde consumido.")
    kg_consumidos: KilosDeTueste = Field(
        description="Kilos descontados del lote verde."
    )
    gramos_consumidos: int = Field(
        description="Gramos descontados del lote verde."
    )


class TuesteRead(BaseModel):
    """Lectura de una orden de tueste con su merma y trazabilidad."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int = Field(description="Identificador de la orden de tueste.")
    fecha_tueste: datetime = Field(description="Fecha y hora del tueste.")
    tipo_de_cafe_id: Optional[int] = Field(
        default=None,
        description="Tipo de café verde procesado; puede ser nulo en órdenes históricas.",
    )
    kg_gastados: KilosDeTueste = Field(description="Kilos de café verde consumidos.")
    kg_obtenidos: KilosDeTueste = Field(description="Kilos de café tostado obtenidos.")
    gramos_gastados: int = Field(description="Gramos de café verde consumidos.")
    gramos_obtenidos: int = Field(description="Gramos de café tostado obtenidos.")
    merma_gramos: int = Field(description="Diferencia entre gramos verdes y tostados.")
    merma_porcentaje: Decimal = Field(
        description="Porcentaje de merma sobre los gramos verdes."
    )
    lote_tostado_id: Optional[int] = Field(
        default=None,
        description="Lote tostado generado por la orden, si ya existe.",
    )
    consumos: list[ConsumoLoteRead] = Field(
        default_factory=list,
        description="Lotes verdes descontados por esta orden.",
    )
