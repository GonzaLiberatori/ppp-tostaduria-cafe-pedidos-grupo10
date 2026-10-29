import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TipoCliente(str, enum.Enum):
    B2B = "B2B"
    B2C = "B2C"


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = (
        CheckConstraint(
            "kilos_comprados >= 0",
            name="ck_clientes_kilos_no_negativos",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo: Mapped[TipoCliente] = mapped_column(
        Enum(
            TipoCliente,
            name="tipo_cliente",
            values_callable=lambda valores: [valor.value for valor in valores],
        ),
        nullable=False,
        default=TipoCliente.B2C,
    )
    kilos_comprados: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )
    # Puede ser negativa: representa un saldo a favor del cliente.
    # No se restringe a >= 0 para no bloquear pagos ni compras posteriores.
    deuda_pendiente: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    @property
    def tiene_deuda(self) -> bool:
        return self.deuda_pendiente > 0
