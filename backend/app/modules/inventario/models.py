import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LoteTipo(str, enum.Enum):
    VERDE = "VERDE"
    TOSTADO = "TOSTADO"


class LoteEstado(str, enum.Enum):
    CERRADO = "CERRADO"
    ABIERTO = "ABIERTO"


class Pais(Base):
    __tablename__ = "pais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)

    regiones: Mapped[list["Region"]] = relationship(back_populates="pais")


class Region(Base):
    __tablename__ = "region"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    pais_id: Mapped[int] = mapped_column(ForeignKey("pais.id"), nullable=False, index=True)

    pais: Mapped["Pais"] = relationship(back_populates="regiones")
    tipos_de_cafe: Mapped[list["TipoDeCafe"]] = relationship(back_populates="region")


class Variedad(Base):
    __tablename__ = "variedad"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)

    tipos_de_cafe: Mapped[list["TipoDeCafe"]] = relationship(back_populates="variedad")


class TipoDeCafe(Base):
    __tablename__ = "tipo_de_cafe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organico: Mapped[bool] = mapped_column(Boolean, nullable=False)
    precio_por_kg_verde: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id"), nullable=False, index=True)
    variedad_id: Mapped[int] = mapped_column(ForeignKey("variedad.id"), nullable=False, index=True)

    region: Mapped["Region"] = relationship(back_populates="tipos_de_cafe")
    variedad: Mapped["Variedad"] = relationship(back_populates="tipos_de_cafe")
    lotes: Mapped[list["Lote"]] = relationship(back_populates="tipo_de_cafe")
    blends: Mapped[list["BlendHasTipoDeCafe"]] = relationship(back_populates="tipo_de_cafe")


class Blend(Base):
    __tablename__ = "blend"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    precio_por_kg_verde: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)

    tipos_de_cafe: Mapped[list["BlendHasTipoDeCafe"]] = relationship(back_populates="blend")
    lotes: Mapped[list["Lote"]] = relationship(back_populates="blend")


class BlendHasTipoDeCafe(Base):
    __tablename__ = "blend_has_tipo_de_cafe"

    blend_id: Mapped[int] = mapped_column(ForeignKey("blend.id"), primary_key=True)
    tipo_de_cafe_id: Mapped[int] = mapped_column(ForeignKey("tipo_de_cafe.id"), primary_key=True)
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    blend: Mapped["Blend"] = relationship(back_populates="tipos_de_cafe")
    tipo_de_cafe: Mapped["TipoDeCafe"] = relationship(back_populates="blends")


class Lote(Base):
    __tablename__ = "lote"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # MEDIUMINT UNSIGNED compatible
    tipo: Mapped[LoteTipo] = mapped_column(
        Enum(LoteTipo, values_callable=lambda e: [m.value for m in e], native_enum=True, name="lote_tipo_enum"),
        nullable=False,
    )
    estado: Mapped[LoteEstado] = mapped_column(
        Enum(LoteEstado, values_callable=lambda e: [m.value for m in e], native_enum=True, name="lote_estado_enum"),
        nullable=False,
    )
    fecha_vencimiento: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    humedad: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    kg_disponibles: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    kg_reales: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    ubicacion_fisica: Mapped[str] = mapped_column(String(50), nullable=False)
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tipo_de_cafe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tipo_de_cafe.id"), nullable=True, index=True)
    blend_id: Mapped[Optional[int]] = mapped_column(ForeignKey("blend.id"), nullable=True, index=True)
    orden_tueste_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orden_tueste.id"), nullable=True, index=True)

    tipo_de_cafe: Mapped[Optional["TipoDeCafe"]] = relationship(back_populates="lotes")
    blend: Mapped[Optional["Blend"]] = relationship(back_populates="lotes")
    orden_tueste: Mapped[Optional["object"]] = relationship()
