"""Configuración de conexión a base de datos.

Crea el engine de SQLAlchemy y la fábrica de sesiones. Los modelos se importan
al final para que SQLAlchemy los registre en ``Base.metadata`` antes de crear
tablas o generar migraciones.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from app.core.config import settings


def get_connect_args(database_url: str) -> dict:
    """Devuelve los argumentos de conexión según el motor de base de datos."""
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {"charset": "utf8mb4"}


def get_pool_class(database_url: str):
    """Devuelve la clase de pool adecuada para el motor configurado."""
    if database_url.startswith("sqlite"):
        return StaticPool
    return QueuePool


def get_engine_kwargs(database_url: str) -> dict:
    """Arma los kwargs del engine según el motor de base de datos."""
    kwargs = {
        "pool_pre_ping": True,  # Verifica la conexión antes de usarla
        "poolclass": get_pool_class(database_url),
        "connect_args": get_connect_args(database_url),
    }
    if not database_url.startswith("sqlite"):
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
    return kwargs


engine = create_engine(
    settings.DATABASE_URL,
    **get_engine_kwargs(settings.DATABASE_URL),
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Provee una sesión de base de datos para cada request.

    La sesión se crea al inicio del request y se cierra automáticamente al
    finalizar, garantizando que no queden conexiones abiertas.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Modelos y metadata
# ---------------------------------------------------------------------------
# Los modelos NO se importan acá para evitar ciclos de importación: cada
# módulo importa los suyos y ``alembic/env.py`` los carga todos antes de
# generar migraciones. ``Base.metadata`` se completa a medida que los routers
# y los tests importan sus modelos.
