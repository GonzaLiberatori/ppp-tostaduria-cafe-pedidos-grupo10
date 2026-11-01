"""Fixtures propias del módulo de pedidos.

Solo reemplaza la sesión de base de datos: los tests de router hablan con la API
desde el hilo de ``TestClient`` y necesitan ver las mismas tablas que la
fixture. Es el mismo patrón que usa ``tests/modules/ventas/conftest.py``.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base


@pytest.fixture
def db_session():
    """Sesión sobre una SQLite en memoria compartida entre hilos."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    sesion = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield sesion
    finally:
        sesion.close()
        engine.dispose()
