from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base declarativa de todos los modelos."""


connect_args: dict[str, bool] = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # Permite compartir la conexión entre hilos en los tests con SQLite.
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Entrega una sesión de SQLAlchemy y la cierra al finalizar la petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
