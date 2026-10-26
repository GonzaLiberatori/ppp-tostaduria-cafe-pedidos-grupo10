"""Dependencias compartidas de la aplicación.

Provee la sesión de base de datos y otras dependencias comunes que se inyectan
en los endpoints de FastAPI vía Depends().
"""

from typing import Generator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal


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
