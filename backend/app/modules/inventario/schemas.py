"""Schemas Pydantic del módulo de inventario.

Contratos de entrada y salida de la API para TipoDeCafe, Blend y Lote.

Reglas de opcionalidad aplicadas a todas las entidades:

- **Create**: solo son obligatorios los atributos que en el modelo no admiten nulo.
- **Update**: todos los atributos editables son opcionales.
- **Read**: siempre incluye el `id` y devuelve todos los datos de la clase;
  los atributos nullable pueden volver ``None``.
- **Delete**: no tiene schema propio. El ``id`` viaja como parámetro de ruta del
  endpoint, de modo que un cuerpo con solo ``id`` sería redundante.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.inventario.models import Blend, LoteEstado, LoteTipo

# ---------------------------------------------------------------------------
# Precisión decimal: espejo exacto de las columnas Numeric(...) de models.py.
# Validar en el borde evita que el error real aparezca como truncamiento
# silencioso de MySQL (ver design.md, Decisions).
# ---------------------------------------------------------------------------
PrecioPorKgVerde = Annotated[Decimal, Field(max_digits=10, decimal_places=2, gt=0)]
Kilos = Annotated[Decimal, Field(max_digits=10, decimal_places=2, ge=0)]
HumedadPorcentaje = Annotated[Decimal, Field(max_digits=5, decimal_places=2, ge=0, le=100)]
PorcentajeBlend = Annotated[Decimal, Field(max_digits=5, decimal_places=2, gt=0)]

# Cantidad de caracteres de String(...) en models.py.
_LONGITUD_NOMBRE = 50
_LONGITUD_UBICACION = 50

# Tolerancia de suma de porcentajes de un blend: acepta 100,00 y también 99,99,
# que es lo que dan tres terceros redondeados a dos decimales.
_SUMA_MINIMA = Decimal("99.99")
_SUMA_MAXIMA = Decimal("100.00")

# Mínimo de tipos de café que integra un blend.
_MINIMA_COMPOSICION = 2


def _validar_composicion(tipos_de_cafe: "list[BlendComposicionItem]") -> None:
    """Valida que una composición de blend sea consistente.

    Exige tipos de café sin repetir y una suma de porcentajes entre 99,99 y
    100,00 inclusive: 0,01 de tolerancia por el redondeo a dos decimales.
    Con precisión de dos decimales esos dos son los únicos valores del rango,
    así que no queda zona gris.
    """
    identificadores = [item.tipo_de_cafe_id for item in tipos_de_cafe]
    if len(identificadores) != len(set(identificadores)):
        raise ValueError("Un blend no puede repetir el mismo tipo de café en su composición.")

    total = sum((item.porcentaje for item in tipos_de_cafe), Decimal("0")).quantize(Decimal("0.01"))
    if not (_SUMA_MINIMA <= total <= _SUMA_MAXIMA):
        raise ValueError(
            f"Los porcentajes de la composición deben sumar entre 99.99 y 100.00, suman {total}."
        )


# ---------------------------------------------------------------------------
# TipoDeCafe
# ---------------------------------------------------------------------------
class TipoDeCafeCreate(BaseModel):
    """Alta de tipo de café. Recibe los nombres de origen como texto."""

    model_config = ConfigDict(extra="forbid")

    organico: bool = Field(description="Indica si el café se produce en condiciones orgánicas.")
    precio_por_kg_verde: PrecioPorKgVerde = Field(description="Precio por kilo de café verde.")
    variedad: str = Field(
        min_length=1,
        max_length=_LONGITUD_NOMBRE,
        description="Nombre de la variedad de café de origen.",
    )
    region: str = Field(
        min_length=1,
        max_length=_LONGITUD_NOMBRE,
        description="Nombre de la región de origen.",
    )
    pais: str = Field(
        min_length=1,
        max_length=_LONGITUD_NOMBRE,
        description="Nombre del país de origen.",
    )


class TipoDeCafeUpdate(BaseModel):
    """Edición de tipo de café. Todos los atributos son opcionales."""

    model_config = ConfigDict(extra="forbid")

    organico: Optional[bool] = Field(default=None, description="Indica si el café se produce en condiciones orgánicas.")
    precio_por_kg_verde: Optional[PrecioPorKgVerde] = Field(
        default=None, description="Precio por kilo de café verde."
    )
    variedad: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=_LONGITUD_NOMBRE,
        description="Nombre de la variedad de café de origen.",
    )
    region: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=_LONGITUD_NOMBRE,
        description="Nombre de la región de origen.",
    )
    pais: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=_LONGITUD_NOMBRE,
        description="Nombre del país de origen.",
    )


class TipoDeCafeRead(BaseModel):
    """Lectura de tipo de café.

    El identificador del tipo de café es su ``id``; ``variedad``, ``region`` y
    ``pais`` son atributos de texto descriptivos, no claves, por lo que este
    schema no expone ``variedad_id`` ni ``region_id``. El modelo y este schema
    comparten exactamente los mismos campos, así que se construye desde el ORM
    sin adaptador: ``TipoDeCafeRead.model_validate(tipo)``.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int = Field(description="Identificador del tipo de café. Es su clave.")
    organico: bool = Field(description="Indica si el café se produce en condiciones orgánicas.")
    precio_por_kg_verde: PrecioPorKgVerde = Field(description="Precio por kilo de café verde.")
    variedad: str = Field(max_length=_LONGITUD_NOMBRE, description="Nombre de la variedad de café de origen.")
    region: str = Field(max_length=_LONGITUD_NOMBRE, description="Nombre de la región de origen.")
    pais: str = Field(max_length=_LONGITUD_NOMBRE, description="Nombre del país de origen.")


# ---------------------------------------------------------------------------
# Blend
# ---------------------------------------------------------------------------
class BlendComposicionItem(BaseModel):
    """Proporción de un tipo de café dentro de la composición de un blend."""

    model_config = ConfigDict(extra="forbid")

    tipo_de_cafe_id: int = Field(description="Identificador del tipo de café que integra el blend.")
    porcentaje: PorcentajeBlend = Field(description="Proporción del tipo de café en el blend, de 0 a 100.")


class BlendCreate(BaseModel):
    """Alta de blend, incluyendo su composición completa de tipos de café."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=_LONGITUD_NOMBRE, description="Nombre comercial del blend.")
    precio_por_kg_verde: PrecioPorKgVerde = Field(description="Precio por kilo de café verde del blend.")
    descripcion: str = Field(description="Descripción del blend.")
    tipos_de_cafe: list[BlendComposicionItem] = Field(
        min_length=_MINIMA_COMPOSICION,
        description="Composición del blend; reemplaza la lista completa en cada escritura.",
    )

    @model_validator(mode="after")
    def _composicion_consistente(self) -> "BlendCreate":
        _validar_composicion(self.tipos_de_cafe)
        return self


class BlendUpdate(BaseModel):
    """Edición de blend. Todos los atributos son opcionales."""

    model_config = ConfigDict(extra="forbid")

    nombre: Optional[str] = Field(
        default=None, min_length=1, max_length=_LONGITUD_NOMBRE, description="Nombre comercial del blend."
    )
    precio_por_kg_verde: Optional[PrecioPorKgVerde] = Field(
        default=None, description="Precio por kilo de café verde del blend."
    )
    descripcion: Optional[str] = Field(default=None, description="Descripción del blend.")
    tipos_de_cafe: Optional[list[BlendComposicionItem]] = Field(
        default=None,
        min_length=_MINIMA_COMPOSICION,
        description="Reemplaza por completo la composición anterior cuando se envía.",
    )

    @model_validator(mode="after")
    def _composicion_consistente(self) -> "BlendUpdate":
        if self.tipos_de_cafe is not None:
            _validar_composicion(self.tipos_de_cafe)
        return self


class BlendRead(BaseModel):
    """Lectura de blend con su composición completa."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(description="Identificador del blend. Es su clave.")
    nombre: str = Field(max_length=_LONGITUD_NOMBRE, description="Nombre comercial del blend.")
    precio_por_kg_verde: PrecioPorKgVerde = Field(description="Precio por kilo de café verde del blend.")
    descripcion: str = Field(description="Descripción del blend.")
    tipos_de_cafe: list[BlendComposicionItem] = Field(description="Composición actual del blend.")

    @classmethod
    def desde_orm(cls, blend: "Blend") -> "BlendRead":
        """Pasa el objeto ORM al contrato de lectura.

        Único adaptador de la capa de schemas: ``blend.tipos_de_cafe`` son filas
        de `BlendHasTipoDeCafe` con atributos de más, y este contrato solo debe
        entregar el par ``tipo_de_cafe_id`` + ``porcentaje`` de cada una.
        """
        return cls(
            id=blend.id,
            nombre=blend.nombre,
            precio_por_kg_verde=blend.precio_por_kg_verde,
            descripcion=blend.descripcion,
            tipos_de_cafe=[
                BlendComposicionItem(
                    tipo_de_cafe_id=fila.tipo_de_cafe_id,
                    porcentaje=fila.porcentaje,
                )
                for fila in blend.tipos_de_cafe
            ],
        )


# ---------------------------------------------------------------------------
# Lote
# ---------------------------------------------------------------------------
class LoteCreate(BaseModel):
    """Alta de lote.

    Los cuatro atributos nullable del modelo no son obligatorios, y
    ``kg_disponibles`` no se solicita: lo deriva el servicio a partir de
    ``kg_reales`` para que no haya dos fuentes de verdad del mismo número.
    """

    model_config = ConfigDict(extra="forbid")

    tipo: LoteTipo = Field(description="Naturaleza del lote, VERDE o TOSTADO.")
    estado: LoteEstado = Field(description="Estado del lote, CERRADO o ABIERTO.")
    fecha_vencimiento: datetime = Field(description="Fecha y hora de vencimiento del lote.")
    humedad: HumedadPorcentaje = Field(description="Humedad medida del café, en porcentaje, de 0 a 100.")
    kg_reales: Kilos = Field(description="Kilos reales pesados del lote.")
    ubicacion_fisica: str = Field(
        min_length=1,
        max_length=_LONGITUD_UBICACION,
        description="Ubicación física del lote dentro del depósito.",
    )
    observaciones: Optional[str] = Field(default=None, description="Observaciones libres del lote.")
    tipo_de_cafe_id: Optional[int] = Field(
        default=None, description="Identificador del tipo de café asociado, si corresponde."
    )
    blend_id: Optional[int] = Field(default=None, description="Identificador del blend asociado, si corresponde.")
    orden_tueste_id: Optional[int] = Field(
        default=None, description="Identificador de la orden de tueste asociada, si corresponde."
    )

    @model_validator(mode="after")
    def _origen_unico(self) -> "LoteCreate":
        """El lote nace de un tipo de café o de un blend, nunca de los dos."""
        if self.tipo_de_cafe_id is None and self.blend_id is None:
            raise ValueError("El lote debe indicar un origen: tipo_de_cafe_id o blend_id.")
        elif self.tipo_de_cafe_id is not None and self.blend_id is not None:
            raise ValueError("El lote no puede indicar tipo_de_cafe_id y blend_id a la vez.")
        return self

    @model_validator(mode="after")
    def _orden_tueste_según_el_tipo(self) -> "LoteCreate":
        """VERDE no tiene orden de tueste; TOSTADO sí, obligatoriamente."""
        if self.tipo == LoteTipo.VERDE and self.orden_tueste_id is not None:
            raise ValueError("Un lote VERDE no puede llevar orden de tueste asociada.")
        elif self.tipo == LoteTipo.TOSTADO and self.orden_tueste_id is None:
            raise ValueError("Un lote TOSTADO debe indicar su orden de tueste.")
        return self


class LoteUpdate(BaseModel):
    """Edición de lote.

    No declara ``tipo``, ``tipo_de_cafe_id``, ``blend_id`` ni
    ``orden_tueste_id``: con ``extra="forbid"`` quedan rechazados
    automáticamente, así que ese atributo no se puede modificar por aquí.
    """

    model_config = ConfigDict(extra="forbid")

    estado: Optional[LoteEstado] = Field(default=None, description="Estado del lote, CERRADO o ABIERTO.")
    fecha_vencimiento: Optional[datetime] = Field(
        default=None, description="Fecha y hora de vencimiento del lote."
    )
    humedad: Optional[HumedadPorcentaje] = Field(default=None, description="Humedad medida del café, en porcentaje.")
    kg_disponibles: Optional[Kilos] = Field(default=None, description="Kilos disponibles para despacho.")
    kg_reales: Optional[Kilos] = Field(default=None, description="Kilos reales pesados del lote.")
    ubicacion_fisica: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=_LONGITUD_UBICACION,
        description="Ubicación física del lote dentro del depósito.",
    )
    observaciones: Optional[str] = Field(default=None, description="Observaciones libres del lote.")


class LoteRead(BaseModel):
    """Lectura de lote con todos sus atributos, nullable admitidos como ``None``.

    Los campos coinciden uno a uno con las columnas de ``Lote``, así que se
    construye desde el ORM sin adaptador: ``LoteRead.model_validate(lote)``.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int = Field(description="Identificador del lote. Es su clave.")
    tipo: LoteTipo = Field(description="Naturaleza del lote, VERDE o TOSTADO.")
    estado: LoteEstado = Field(description="Estado del lote, CERRADO o ABIERTO.")
    fecha_vencimiento: datetime = Field(description="Fecha y hora de vencimiento del lote.")
    humedad: HumedadPorcentaje = Field(description="Humedad medida del café, en porcentaje.")
    kg_disponibles: Kilos = Field(description="Kilos disponibles para despacho.")
    kg_reales: Kilos = Field(description="Kilos reales pesados del lote.")
    ubicacion_fisica: str = Field(max_length=_LONGITUD_UBICACION, description="Ubicación física del lote.")
    observaciones: Optional[str] = Field(default=None, description="Observaciones libres del lote.")
    tipo_de_cafe_id: Optional[int] = Field(
        default=None, description="Identificador del tipo de café asociado, si corresponde."
    )
    blend_id: Optional[int] = Field(default=None, description="Identificador del blend asociado, si corresponde.")
    orden_tueste_id: Optional[int] = Field(
        default=None, description="Identificador de la orden de tueste asociada, si corresponde."
    )


# ---------------------------------------------------------------------------
# Ediciones puntuales de Lote: el id entra por ruta y el cuerpo lleva un
# solo atributo, para que el endpoint prometa exactamente una cosa.
# ---------------------------------------------------------------------------
class LoteKgDisponiblesUpdate(BaseModel):
    """Corrige los kilos disponibles de un lote identificado por id."""

    model_config = ConfigDict(extra="forbid")

    kg_disponibles: Kilos = Field(description="Nuevo valor de kilos disponibles para despacho.")


class LoteKgRealesUpdate(BaseModel):
    """Corrige los kilos reales de un lote identificado por id."""

    model_config = ConfigDict(extra="forbid")

    kg_reales: Kilos = Field(description="Nuevo valor de kilos reales pesados.")


class LoteEstadoUpdate(BaseModel):
    """Cambia el estado de un lote identificado por id."""

    model_config = ConfigDict(extra="forbid")

    estado: LoteEstado = Field(description="Nuevo estado del lote, CERRADO o ABIERTO.")
