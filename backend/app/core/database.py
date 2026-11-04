"""Configuración de conexión a base de datos.

Crea el engine de SQLAlchemy y la fábrica de sesiones. Los modelos se importan
acá para que SQLAlchemy los registre en metadata antes de crear tablas.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine y Session
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verifica conexión antes de usarla
    echo=settings.DEBUG,  # Log de SQL solo en modo debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Base declarativa para modelos
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""

    pass


# ---------------------------------------------------------------------------
# Importar modelos para que SQLAlchemy los conozca
# ---------------------------------------------------------------------------
# Es CRUCIAL importar los modelos DESPUÉS de definir Base, para que se
# registren en Base.metadata. Esto permite que create_all() y las migraciones
# de Alembic detecten las tablas correctamente.
from app.modules.inventario.models import (  # noqa: E402, F401
    Blend,
    BlendHasTipoDeCafe,
    Lote,
    TipoDeCafe,
)
