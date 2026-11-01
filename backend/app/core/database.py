"""Configuración de conexión a base de datos.

Crea el engine de SQLAlchemy y la fábrica de sesiones sobre SQLite, el único
motor soportado por el proyecto. Los modelos se importan desde los módulos
(cada uno registra los suyos en ``Base.metadata``), y ``alembic/env.py`` los
carga todos antes de generar migraciones.
"""

from typing import Any, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def es_sqlite_en_memoria(url: str) -> bool:
    """Indica si la URL corresponde a una base SQLite en memoria."""
    return ":memory:" in url


def configurar_sqlite(dbapi_connection: Any, _connection_record: Any) -> None:
    """Activa las claves foráneas en cada conexión.

    SQLite ignora las restricciones de clave foránea por defecto; sin este
    PRAGMA las relaciones entre tablas no se validan.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


opciones_engine: dict[str, Any] = {
    # FastAPI atiende requests en varios hilos; SQLite no permite compartir
    # conexiones entre hilos salvo que se desactive esta comprobación.
    "connect_args": {"check_same_thread": False},
    "echo": settings.DEBUG,
}

if es_sqlite_en_memoria(settings.DATABASE_URL):
    # Una base en memoria existe mientras viva su conexión: StaticPool mantiene
    # una única conexión compartida para todos los requests y tests.
    opciones_engine["poolclass"] = StaticPool

engine = create_engine(settings.DATABASE_URL, **opciones_engine)

event.listen(engine, "connect", configurar_sqlite)

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
