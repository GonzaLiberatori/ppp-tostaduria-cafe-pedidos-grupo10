from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Stock(Base):
    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # verde, tostado
    variedad: Mapped[str] = mapped_column(String(100), nullable=False)
    origen: Mapped[str] = mapped_column(String(100), nullable=False)
    precio_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    lote_principal: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_ingreso: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    bolsas: Mapped[list["Bolsa"]] = relationship(
        "Bolsa",
        back_populates="stock",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Stock(id={self.id}, variedad={self.variedad}, tipo={self.tipo})>"


class Bolsa(Base):
    __tablename__ = "bolsas"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    stock_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("stock.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False)  # cerrada, abierta
    kilos: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lote_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    stock = relationship("Stock", back_populates="bolsas", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Bolsa(id={self.id}, stock_id={self.stock_id}, estado={self.estado}, kilos={self.kilos})>"