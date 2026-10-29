from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PlainSerializer,
    field_validator,
)
from pydantic.alias_generators import to_camel

from app.modules.clientes.models import Cliente, TipoCliente

# En la base se usa Decimal; en JSON se expone como número para el frontend.
DecimalNumero = Annotated[
    Decimal,
    PlainSerializer(float, return_type=float, when_used="json"),
]

ALIAS_DEUDA = AliasChoices(
    "montoDeuda",
    "monto_deuda",
    "deudaPendiente",
    "deuda_pendiente",
)


class _ClienteBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    nombre: str = Field(min_length=1, max_length=150)
    tipo: TipoCliente = TipoCliente.B2C
    kilos_comprados: Annotated[
        Decimal,
        Field(ge=0, max_digits=10, decimal_places=2),
    ] = Decimal("0")
    # Sin ge=0: un saldo negativo representa crédito a favor del cliente y
    # no debe impedir registrar la compra ni rechazar el alta del cliente.
    deuda_pendiente: Annotated[
        Decimal,
        Field(max_digits=12, decimal_places=2),
    ] = Field(default=Decimal("0"), validation_alias=ALIAS_DEUDA)
    telefono: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    direccion: str | None = Field(default=None, max_length=255)

    # El frontend envía este booleano, pero la deuda se deriva del monto.
    tiene_deuda: bool | None = Field(default=None, exclude=True)

    @field_validator("email", mode="before")
    @classmethod
    def email_vacio_a_none(cls, valor: object) -> object:
        if isinstance(valor, str) and not valor.strip():
            return None
        return valor

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede estar vacío")
        return valor


class ClienteCreate(_ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    tipo: TipoCliente | None = None
    kilos_comprados: Annotated[
        Decimal,
        Field(ge=0, max_digits=10, decimal_places=2),
    ] | None = None
    # Igual que en el alta: se admite saldo a favor (negativo).
    deuda_pendiente: Annotated[
        Decimal,
        Field(max_digits=12, decimal_places=2),
    ] | None = Field(default=None, validation_alias=ALIAS_DEUDA)
    telefono: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    direccion: str | None = Field(default=None, max_length=255)
    tiene_deuda: bool | None = Field(default=None, exclude=True)

    @field_validator("email", mode="before")
    @classmethod
    def email_vacio_a_none(cls, valor: object) -> object:
        if isinstance(valor, str) and not valor.strip():
            return None
        return valor

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede estar vacío")
        return valor


class ClienteOut(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    id: int
    nombre: str
    tipo: TipoCliente
    kilos_comprados: DecimalNumero
    tiene_deuda: bool | None = None
    deuda_pendiente: DecimalNumero | None = Field(
        default=None,
        serialization_alias="montoDeuda",
    )
    telefono: str = ""
    email: str = ""
    direccion: str = ""
    creado_en: datetime

    @classmethod
    def desde_modelo(cls, cliente: Cliente, incluir_deuda: bool) -> "ClienteOut":
        """Serializa el cliente; la deuda solo se incluye para ADMIN."""
        return cls(
            id=cliente.id,
            nombre=cliente.nombre,
            tipo=cliente.tipo,
            kilos_comprados=cliente.kilos_comprados,
            tiene_deuda=cliente.tiene_deuda if incluir_deuda else None,
            deuda_pendiente=cliente.deuda_pendiente if incluir_deuda else None,
            telefono=cliente.telefono or "",
            email=cliente.email or "",
            direccion=cliente.direccion or "",
            creado_en=cliente.creado_en,
        )
